import type { AssessmentRoundPackage, CachedAssessmentPackage } from "../types";

const DATABASE_NAME = "ucmb-dqa-offline";
const DATABASE_VERSION = 1;
const STORE_NAME = "assessment-packages";

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = window.indexedDB.open(DATABASE_NAME, DATABASE_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        database.createObjectStore(STORE_NAME, { keyPath: "assessment_facility_id" });
      }
    };
  });
}

export async function saveCachedAssessment(
  assessmentFacilityId: string,
  payload: AssessmentRoundPackage,
): Promise<CachedAssessmentPackage> {
  const database = await openDatabase();
  const cachedRecord: CachedAssessmentPackage = {
    assessment_facility_id: assessmentFacilityId,
    round_details: payload.assessment_round,
    facility_details: payload.facility,
    selected_indicators: payload.selected_indicators,
    source_document_requirements: payload.source_document_requirements,
    status: payload.status,
    deadline: payload.deadline,
    fetched_at: new Date().toISOString(),
    cache_version: payload.offline_cache_version,
  };

  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    const request = store.put(cachedRecord);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(cachedRecord);
  });
}

export async function getCachedAssessment(assessmentFacilityId: string): Promise<CachedAssessmentPackage | null> {
  const database = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readonly");
    const store = transaction.objectStore(STORE_NAME);
    const request = store.get(assessmentFacilityId);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve((request.result as CachedAssessmentPackage | undefined) ?? null);
  });
}
