import type {
  AssessmentDraft,
  AssessmentWorkspace,
  CachedAssessmentWorkspace,
  Dhis2Value,
  PendingSyncQueueItem,
  SyncAssessmentDraftResponse,
  SyncHistoryRecord,
} from "../types";

const DATABASE_NAME = "ucmb-dqa-offline";
const DATABASE_VERSION = 4;
const CACHED_ASSESSMENTS_STORE = "cached_assessments";
const ASSESSMENT_DRAFTS_STORE = "assessment_drafts";
const PENDING_SYNC_QUEUE_STORE = "pending_sync_queue";
const SYNC_HISTORY_STORE = "sync_history";
const CACHED_DHIS2_VALUES_STORE = "cached_dhis2_values";

export const OFFLINE_STORE_EVENT = "ucmb-offline-store-updated";

interface StoredDhis2Values {
  assessment_facility_id: string;
  values: Dhis2Value[];
  saved_at: string;
}

function broadcastOfflineStoreUpdate() {
  window.dispatchEvent(new CustomEvent(OFFLINE_STORE_EVENT));
}

function createStoreIfMissing(database: IDBDatabase, storeName: string, keyPath: string, autoIncrement = false) {
  if (!database.objectStoreNames.contains(storeName)) {
    database.createObjectStore(storeName, { keyPath, autoIncrement });
  }
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = window.indexedDB.open(DATABASE_NAME, DATABASE_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = () => {
      const database = request.result;
      createStoreIfMissing(database, CACHED_ASSESSMENTS_STORE, "assessment_facility_id");
      createStoreIfMissing(database, ASSESSMENT_DRAFTS_STORE, "assessment_facility_id");
      createStoreIfMissing(database, PENDING_SYNC_QUEUE_STORE, "assessment_facility_id");
      createStoreIfMissing(database, CACHED_DHIS2_VALUES_STORE, "assessment_facility_id");
      createStoreIfMissing(database, SYNC_HISTORY_STORE, "id");
    };
  });
}

async function runStoreOperation<T>(
  storeName: string,
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore, resolve: (value: T) => void, reject: (reason?: unknown) => void) => void,
): Promise<T> {
  const database = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(storeName, mode);
    const store = transaction.objectStore(storeName);
    operation(store, resolve, reject);
  });
}

function mapWorkspaceDhis2Values(workspace: AssessmentWorkspace): Dhis2Value[] {
  return workspace.values.map((value) => ({
    indicator_id: value.indicator_id,
    dhis2_uid_or_operand:
      workspace.selected_indicators.find((indicator) => indicator.indicator_id === value.indicator_id)?.dhis2_uid_or_operand ??
      null,
    value: value.dhis2_value_at_assessment,
    status: value.dhis2_api_status ?? "PENDING",
    error: value.dhis2_error_message,
    extracted_at: value.dhis2_extracted_at,
  }));
}

function toPendingQueueItem(draft: AssessmentDraft): PendingSyncQueueItem {
  return {
    assessment_facility_id: draft.assessment_facility_id,
    client_draft_id: draft.client_draft_id,
    client_batch_id: draft.client_batch_id,
    submit_final: draft.submit_final,
    sync_status: draft.sync_status,
    last_saved_at: draft.last_saved_at,
    last_sync_attempt_at: draft.last_sync_attempt_at,
    last_synced_at: draft.last_synced_at,
    error_message: draft.error_message,
  };
}

function buildHistoryRecord(
  assessmentFacilityId: string,
  payload: SyncAssessmentDraftResponse,
  message: string,
): SyncHistoryRecord {
  return {
    id: `${assessmentFacilityId}:${payload.synced_at}:${Math.random().toString(16).slice(2)}`,
    assessment_facility_id: assessmentFacilityId,
    client_batch_id: payload.duplicate_batch ? `${assessmentFacilityId}:duplicate` : `${assessmentFacilityId}:${payload.synced_at}`,
    status:
      payload.status === "SYNCED"
        ? "SYNCED"
        : payload.status === "RELOGIN_REQUIRED"
          ? "RELOGIN_REQUIRED"
          : "FAILED",
    synced_at: payload.synced_at,
    message,
    items_received: payload.items_received,
    items_saved: payload.items_saved,
  };
}

export async function initOfflineStore() {
  await openDatabase();
}

export async function saveCachedAssessment(workspace: AssessmentWorkspace): Promise<CachedAssessmentWorkspace> {
  const record: CachedAssessmentWorkspace = {
    assessment_facility_id: workspace.assessment_facility.id,
    workspace,
    assessment_status: workspace.assessment_facility.status,
    workspace_mode: workspace.workspace_mode,
    fetched_at: new Date().toISOString(),
    cache_version: workspace.offline_cache_version,
  };

  await runStoreOperation<void>(CACHED_ASSESSMENTS_STORE, "readwrite", (store, resolve, reject) => {
    const request = store.put(record);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
  await saveDhis2Values(workspace.assessment_facility.id, mapWorkspaceDhis2Values(workspace));
  broadcastOfflineStoreUpdate();
  return record;
}

export async function getCachedAssessment(assessmentFacilityId: string): Promise<CachedAssessmentWorkspace | null> {
  return runStoreOperation<CachedAssessmentWorkspace | null>(
    CACHED_ASSESSMENTS_STORE,
    "readonly",
    (store, resolve, reject) => {
      const request = store.get(assessmentFacilityId);
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve((request.result as CachedAssessmentWorkspace | undefined) ?? null);
    },
  );
}

export async function listCachedAssessments(): Promise<CachedAssessmentWorkspace[]> {
  return runStoreOperation<CachedAssessmentWorkspace[]>(CACHED_ASSESSMENTS_STORE, "readonly", (store, resolve, reject) => {
    const request = store.getAll();
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve((request.result as CachedAssessmentWorkspace[]) ?? []);
  });
}

export async function saveAssessmentDraft(draft: AssessmentDraft): Promise<AssessmentDraft> {
  await runStoreOperation<void>(ASSESSMENT_DRAFTS_STORE, "readwrite", (store, resolve, reject) => {
    const request = store.put(draft);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
  await addOrUpdatePendingSyncItem(draft);
  broadcastOfflineStoreUpdate();
  return draft;
}

export async function getAssessmentDraft(assessmentFacilityId: string): Promise<AssessmentDraft | null> {
  return runStoreOperation<AssessmentDraft | null>(ASSESSMENT_DRAFTS_STORE, "readonly", (store, resolve, reject) => {
    const request = store.get(assessmentFacilityId);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve((request.result as AssessmentDraft | undefined) ?? null);
  });
}

export async function deleteAssessmentDraft(assessmentFacilityId: string): Promise<void> {
  await runStoreOperation<void>(ASSESSMENT_DRAFTS_STORE, "readwrite", (store, resolve, reject) => {
    const request = store.delete(assessmentFacilityId);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
  await runStoreOperation<void>(PENDING_SYNC_QUEUE_STORE, "readwrite", (store, resolve, reject) => {
    const request = store.delete(assessmentFacilityId);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
  broadcastOfflineStoreUpdate();
}

export async function listPendingSyncItems(): Promise<AssessmentDraft[]> {
  const queueItems = await runStoreOperation<PendingSyncQueueItem[]>(PENDING_SYNC_QUEUE_STORE, "readonly", (store, resolve, reject) => {
    const request = store.getAll();
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve((request.result as PendingSyncQueueItem[]) ?? []);
  });
  const drafts = await Promise.all(queueItems.map((item) => getAssessmentDraft(item.assessment_facility_id)));
  return drafts.filter(Boolean) as AssessmentDraft[];
}

export async function addOrUpdatePendingSyncItem(draft: AssessmentDraft): Promise<PendingSyncQueueItem> {
  const item = toPendingQueueItem(draft);
  await runStoreOperation<void>(PENDING_SYNC_QUEUE_STORE, "readwrite", (store, resolve, reject) => {
    const request = store.put(item);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
  broadcastOfflineStoreUpdate();
  return item;
}

export async function markDraftPendingSync(assessmentFacilityId: string): Promise<AssessmentDraft | null> {
  const draft = await getAssessmentDraft(assessmentFacilityId);
  if (!draft) {
    return null;
  }
  const updatedDraft: AssessmentDraft = {
    ...draft,
    sync_status: "PENDING_SYNC",
    last_saved_at: new Date().toISOString(),
    error_message: null,
  };
  return saveAssessmentDraft(updatedDraft);
}

export async function markDraftSyncing(assessmentFacilityId: string): Promise<AssessmentDraft | null> {
  const draft = await getAssessmentDraft(assessmentFacilityId);
  if (!draft) {
    return null;
  }
  const updatedDraft: AssessmentDraft = {
    ...draft,
    sync_status: "SYNCING",
    last_sync_attempt_at: new Date().toISOString(),
    error_message: null,
  };
  return saveAssessmentDraft(updatedDraft);
}

export async function markDraftSynced(
  assessmentFacilityId: string,
  serverResponse: SyncAssessmentDraftResponse,
): Promise<AssessmentDraft | null> {
  const draft = await getAssessmentDraft(assessmentFacilityId);
  if (!draft) {
    return null;
  }
  const updatedDraft: AssessmentDraft = {
    ...draft,
    sync_status: "SYNCED",
    last_synced_at: serverResponse.synced_at,
    last_sync_attempt_at: serverResponse.synced_at,
    error_message: null,
  };
  await runStoreOperation<void>(ASSESSMENT_DRAFTS_STORE, "readwrite", (store, resolve, reject) => {
    const request = store.put(updatedDraft);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
  await runStoreOperation<void>(PENDING_SYNC_QUEUE_STORE, "readwrite", (store, resolve, reject) => {
    const request = store.delete(assessmentFacilityId);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
  await saveSyncHistory(
    buildHistoryRecord(
      assessmentFacilityId,
      serverResponse,
      serverResponse.message ?? (serverResponse.duplicate_batch ? "Draft was already synced." : "Synced successfully."),
    ),
  );
  broadcastOfflineStoreUpdate();
  return updatedDraft;
}

export async function markDraftSyncFailed(
  assessmentFacilityId: string,
  errorMessage: string,
  reloginRequired = false,
): Promise<AssessmentDraft | null> {
  const draft = await getAssessmentDraft(assessmentFacilityId);
  if (!draft) {
    return null;
  }
  const updatedDraft: AssessmentDraft = {
    ...draft,
    sync_status: reloginRequired ? "RELOGIN_REQUIRED" : "SYNC_FAILED",
    last_sync_attempt_at: new Date().toISOString(),
    error_message: errorMessage,
  };
  await saveAssessmentDraft(updatedDraft);
  await saveSyncHistory({
    id: `${assessmentFacilityId}:${Date.now()}`,
    assessment_facility_id: assessmentFacilityId,
    client_batch_id: draft.client_batch_id,
    status: reloginRequired ? "RELOGIN_REQUIRED" : "FAILED",
    synced_at: new Date().toISOString(),
    message: errorMessage,
    items_received: draft.values.length + draft.source_document_checks.length,
    items_saved: 0,
  });
  return updatedDraft;
}

export async function clearSyncedDraft(assessmentFacilityId: string): Promise<void> {
  await deleteAssessmentDraft(assessmentFacilityId);
}

export async function saveSyncHistory(syncRecord: SyncHistoryRecord): Promise<SyncHistoryRecord> {
  await runStoreOperation<void>(SYNC_HISTORY_STORE, "readwrite", (store, resolve, reject) => {
    const request = store.put(syncRecord);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
  broadcastOfflineStoreUpdate();
  return syncRecord;
}

export async function getSyncHistory(assessmentFacilityId: string): Promise<SyncHistoryRecord[]> {
  const items = await runStoreOperation<SyncHistoryRecord[]>(SYNC_HISTORY_STORE, "readonly", (store, resolve, reject) => {
    const request = store.getAll();
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve((request.result as SyncHistoryRecord[]) ?? []);
  });
  return items
    .filter((item) => item.assessment_facility_id === assessmentFacilityId)
    .sort((left, right) => right.synced_at.localeCompare(left.synced_at));
}

export async function getPendingSyncCount(): Promise<number> {
  const queueItems = await runStoreOperation<PendingSyncQueueItem[]>(PENDING_SYNC_QUEUE_STORE, "readonly", (store, resolve, reject) => {
    const request = store.getAll();
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve((request.result as PendingSyncQueueItem[]) ?? []);
  });
  return queueItems.filter((item) => item.sync_status !== "SYNCED").length;
}

export async function getFailedSyncCount(): Promise<number> {
  const drafts = await listPendingSyncItems();
  return drafts.filter((item) => item.sync_status === "SYNC_FAILED" || item.sync_status === "RELOGIN_REQUIRED").length;
}

export async function saveDhis2Values(assessmentFacilityId: string, values: Dhis2Value[]): Promise<void> {
  const record: StoredDhis2Values = {
    assessment_facility_id: assessmentFacilityId,
    values,
    saved_at: new Date().toISOString(),
  };
  await runStoreOperation<void>(CACHED_DHIS2_VALUES_STORE, "readwrite", (store, resolve, reject) => {
    const request = store.put(record);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
  broadcastOfflineStoreUpdate();
}

export async function getDhis2Values(assessmentFacilityId: string): Promise<Dhis2Value[]> {
  const record = await runStoreOperation<StoredDhis2Values | null>(
    CACHED_DHIS2_VALUES_STORE,
    "readonly",
    (store, resolve, reject) => {
      const request = store.get(assessmentFacilityId);
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve((request.result as StoredDhis2Values | undefined) ?? null);
    },
  );
  return record?.values ?? [];
}
