/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_USE_DEMO?: string;
  /** When "true", live-API failures surface as errors instead of falling back to demo data. */
  readonly VITE_STRICT_API?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
