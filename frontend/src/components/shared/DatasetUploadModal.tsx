import React, { useState, useRef } from 'react';
import { useVaruna } from '../../context/VarunaContext';
import { uploadDataset } from '../../services/api';
import { Upload, FileText, CheckCircle2, AlertTriangle, Loader2, Database, Sparkles, X } from 'lucide-react';

interface DatasetUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DatasetUploadModal: React.FC<DatasetUploadModalProps> = ({ isOpen, onClose }) => {
  const { refreshData } = useVaruna();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadStage, setUploadStage] = useState<string>('');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  // What the file is. Presets are synthetic; a custom file must be labelled honestly by the uploader.
  const [provenance, setProvenance] = useState<string>('SYNTHETIC_STRESS_TEST');
  const [isPreset, setIsPreset] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      setIsPreset(false); setResult(null);
      setError(null);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setIsPreset(false); setResult(null);
      setError(null);
    }
  };

  const handlePresetSelect = async (presetName: string, contentStr: string) => {
    const blob = new Blob([contentStr], { type: 'text/csv' });
    const file = new File([blob], `${presetName}.csv`, { type: 'text/csv' });
    setSelectedFile(file);
    setIsPreset(true); setProvenance('SYNTHETIC_STRESS_TEST'); setResult(null);
    setError(null);
  };

  const executeIngest = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setError(null);
    setResult(null);

    try {
      setUploadStage('Uploading · SHA-256 checksum · QC · unit harmonisation on the server…');
      const res = await uploadDataset(selectedFile, isPreset ? 'SYNTHETIC_STRESS_TEST' : provenance);
      setResult(res);
      setUploading(false);
      
      // Auto-refresh VARUNA Context
      await refreshData();
    } catch (err: any) {
      setUploading(false);
      setError(err.message || 'Ingestion failed');
    }
  };

  // Pre-configured synthetic CSV presets for quick evaluation
  const presetA = `cycle_id,issue_date,valid_date,region_id,region_name,season,weather_regime,variable,unit,lead_hours,model_id,forecast_value,data_provenance,synthetic
0,2026-06-01,2026-06-02,IN_TELANGANA_DECCAN,Telangana,SW_MONSOON,HEAVY_RAINFALL,rainfall,mm,48,NCUM,92.5,SYNTHETIC_STRESS_TEST,True
0,2026-06-01,2026-06-02,IN_TELANGANA_DECCAN,Telangana,SW_MONSOON,HEAVY_RAINFALL,rainfall,mm,48,GFS,114.2,SYNTHETIC_STRESS_TEST,True
0,2026-06-01,2026-06-02,IN_TELANGANA_DECCAN,Telangana,SW_MONSOON,HEAVY_RAINFALL,rainfall,mm,48,WRF,58.0,SYNTHETIC_STRESS_TEST,True
0,2026-06-01,2026-06-02,IN_TELANGANA_DECCAN,Telangana,SW_MONSOON,HEAVY_RAINFALL,rainfall,mm,48,AI_WEATHER,78.4,SYNTHETIC_STRESS_TEST,True`;

  const presetB = `cycle_id,issue_date,valid_date,region_id,region_name,season,weather_regime,variable,unit,lead_hours,model_id,forecast_value,data_provenance,synthetic
0,2026-06-01,2026-06-02,IN_WESTERN_GHATS_KERALA,Kerala,SW_MONSOON,EXTREME_RAINFALL,rainfall,mm,24,NCUM,145.0,SYNTHETIC_STRESS_TEST,True
0,2026-06-01,2026-06-02,IN_WESTERN_GHATS_KERALA,Kerala,SW_MONSOON,EXTREME_RAINFALL,rainfall,mm,24,GFS,162.0,SYNTHETIC_STRESS_TEST,True
0,2026-06-01,2026-06-02,IN_WESTERN_GHATS_KERALA,Kerala,SW_MONSOON,EXTREME_RAINFALL,rainfall,mm,24,WRF,185.0,SYNTHETIC_STRESS_TEST,True
0,2026-06-01,2026-06-02,IN_WESTERN_GHATS_KERALA,Kerala,SW_MONSOON,EXTREME_RAINFALL,rainfall,mm,24,AI_WEATHER,138.0,SYNTHETIC_STRESS_TEST,True`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-fadeIn">
      <div className="bg-surface-container border border-surface-border rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-4 px-6 border-b border-surface-border bg-surface-container-high/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-600 dark:text-emerald-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-headline font-bold text-lg text-on-surface flex items-center gap-2">
                DATASET INGESTION
              </h2>
              <p className="text-xs font-mono text-on-surface-variant">
                Upload CSV / JSON / NetCDF datasets directly into VARUNA's 14-Stage Canonical Pipeline
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-on-surface-variant hover:text-on-surface rounded-lg hover:bg-surface-container-high transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">
          {/* Preset Buttons for Quick SIH Demonstration */}
          <div>
            <label className="text-xs font-mono uppercase font-bold text-on-surface-variant tracking-wider flex items-center gap-2 mb-2">
              <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
              Quick SIH Evaluation Presets (varuna_feel3)
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => handlePresetSelect('varuna-synth-a-convective', presetA)}
                className="flex flex-col text-left p-3 rounded-lg border border-surface-border bg-surface-container-high/40 hover:bg-surface-container-high hover:border-emerald-500/50 transition-all group"
              >
                <span className="text-xs font-bold text-on-surface group-hover:text-emerald-600">
                  Preset A: Heavy Monsoon (Telangana)
                </span>
                <span className="text-[11px] font-mono text-on-surface-variant mt-1">
                  NCUM 92.5mm | GFS 114.2mm | WRF 58.0mm
                </span>
              </button>

              <button
                type="button"
                onClick={() => handlePresetSelect('varuna-synth-b-extreme', presetB)}
                className="flex flex-col text-left p-3 rounded-lg border border-surface-border bg-surface-container-high/40 hover:bg-surface-container-high hover:border-amber-500/50 transition-all group"
              >
                <span className="text-xs font-bold text-on-surface group-hover:text-amber-600">
                  Preset B: Extreme Cloudburst (Ghats)
                </span>
                <span className="text-[11px] font-mono text-on-surface-variant mt-1">
                  NCUM 145mm | WRF 185mm | Extreme Alert
                </span>
              </button>
            </div>
          </div>

          {/* Drag and Drop Zone */}
          <div>
            <label className="text-xs font-mono uppercase font-bold text-on-surface-variant tracking-wider mb-2 block">
              Custom Dataset File Upload (.csv, .json, .parquet)
            </label>
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-3 ${
                dragActive
                  ? 'border-emerald-500 bg-emerald-500/10'
                  : selectedFile
                  ? 'border-emerald-500/50 bg-surface-container-high/60'
                  : 'border-surface-border hover:border-outline-variant bg-surface-container-high/20 hover:bg-surface-container-high/40'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.json,.jsonl,.parquet,.nc,.zip"
                onChange={handleFileChange}
                className="hidden"
              />

              {selectedFile ? (
                <div className="flex items-center gap-3 text-emerald-600 dark:text-emerald-400">
                  <FileText className="w-8 h-8" />
                  <div className="text-left">
                    <p className="text-sm font-bold text-on-surface">{selectedFile.name}</p>
                    <p className="text-xs font-mono text-on-surface-variant">
                      {(selectedFile.size / 1024).toFixed(1)} KB • Ready for Ingestion
                    </p>
                  </div>
                </div>
              ) : (
                <>
                  <div className="p-3 bg-surface-container-high rounded-full text-on-surface-variant">
                    <Upload className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-on-surface">
                      Drag & drop a forecast or observation file here
                    </p>
                    <p className="text-xs text-on-surface-variant font-mono mt-1">
                      Supports CSV, JSON, NetCDF4, or ZIP Archives
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>

          {selectedFile && !isPreset && (
            <div>
              <label htmlFor="upload-provenance" className="text-xs font-mono uppercase font-bold text-on-surface-variant tracking-wider mb-2 block">
                What is this file?
              </label>
              <select id="upload-provenance" value={provenance} onChange={e => setProvenance(e.target.value)}
                className="w-full p-2 rounded-lg border border-outline-variant/40 bg-surface-container-lowest text-on-surface text-xs font-mono">
                <option value="SYNTHETIC_STRESS_TEST">Synthetic / test data</option>
                <option value="PUBLIC_BENCHMARK">Public reference data (e.g. global models, reanalysis)</option>
                <option value="AUTHORIZED_OPERATIONAL_FEED">Authorised NCMRWF / IMD product</option>
              </select>
              <p className="text-[11px] font-mono text-on-surface-variant mt-1">
                {provenance === 'AUTHORIZED_OPERATIONAL_FEED'
                  ? 'Only for files actually received from NCMRWF or IMD. These take priority over public copies in the blend.'
                  : 'This label is stored with every record and shown wherever the data is used.'}
              </p>
            </div>
          )}

          {/* Progress or Error Display */}
          {uploading && (
            <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-500/30 rounded-lg space-y-2">
              <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 text-xs font-mono font-bold">
                <Loader2 className="w-4 h-4 animate-spin" />
                {uploadStage}
              </div>
              <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full animate-pulse w-3/4 rounded-full" />
              </div>
            </div>
          )}

          {error && (
            <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-500/40 rounded-lg flex items-start gap-3 text-rose-600 dark:text-rose-400 text-xs font-mono">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600 dark:text-rose-400" />
              <div>
                <p className="font-bold">Ingestion Error</p>
                <p className="mt-1 text-on-surface-variant">{error}</p>
              </div>
            </div>
          )}

          {result && (
            <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-500/40 rounded-lg text-xs font-mono space-y-2">
              <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-bold">
                <CheckCircle2 className="w-4 h-4" />
                Dataset ingested ({result.provenance || 'labelled'})
              </div>
              <div className="grid grid-cols-2 gap-2 text-on-surface-variant pt-1">
                <div>Dataset ID: <span className="text-emerald-600 dark:text-emerald-400">{result.dataset_id}</span></div>
                <div>Records ingested: <span className="text-emerald-600 dark:text-emerald-400">{result.records_ingested ?? result.records_processed ?? '—'}</span>
                  {' '}of {result.records_processed ?? '—'}</div>
                <div>Format: <span className="text-on-surface">{result.format || '—'}</span></div>
                <div>Rejected / duplicates: <span className="text-on-surface">{result.records_rejected ?? 0} / {result.duplicates_skipped ?? 0}</span></div>
                <div>Status: <span className="text-emerald-600 dark:text-emerald-400">{result.status || '—'}</span></div>
                {result.checksum_sha256 && <div className="col-span-2 break-all">SHA-256: <span className="text-on-surface">{result.checksum_sha256}</span></div>}
                <div className="col-span-2">The dashboard was refreshed; forecasts now include this file when it matches the selected region, variable and lead time.</div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 px-6 border-t border-surface-border bg-surface-container-high/50 flex items-center justify-between">
          <span className="text-[11px] font-mono text-on-surface-variant">
            CSV · JSON · JSONL · Parquet · NetCDF · ZIP
          </span>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-bold text-on-surface-variant hover:text-on-surface rounded-lg hover:bg-surface-container-high transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={executeIngest}
              disabled={!selectedFile || uploading}
              className="flex items-center gap-2 px-5 py-2 text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-all shadow-md shadow-emerald-950/50"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Ingesting...
                </>
              ) : (
                <>
                  <Database className="w-3.5 h-3.5" />
                  Ingest & Run Pipeline
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
