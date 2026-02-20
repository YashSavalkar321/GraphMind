import { useState, useRef } from 'react';
import { X, Upload, FileText, Loader2, CheckCircle2, AlertCircle, FileUp } from 'lucide-react';
import useAppStore from '../store/useAppStore';

export default function IngestModal() {
  const { isIngestModalOpen, closeIngestModal, ingestDocument, isIngesting, getCurrentUser } =
    useAppStore();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [sourceType, setSourceType] = useState('text');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);
  const currentUser = getCurrentUser();

  if (!isIngestModalOpen) return null;

  /* ── Submit ── */
  const handleIngest = async () => {
    if (!title.trim() || !content.trim()) {
      setError('Both title and content are required.');
      return;
    }
    setError('');
    try {
      const res = await ingestDocument(title.trim(), content.trim(), sourceType);
      setResult(res);
      setTimeout(() => {
        setTitle('');
        setContent('');
        setResult(null);
        setSourceType('text');
      }, 600);
    } catch {
      setError('Ingestion failed. Please try again.');
    }
  };

  const handleClose = () => {
    setTitle('');
    setContent('');
    setResult(null);
    setError('');
    setSourceType('text');
    closeIngestModal();
  };

  /* ── Drag & drop / file read helpers ── */
  const readFile = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      setContent(e.target.result);
      if (!title.trim()) setTitle(file.name.replace(/\.[^.]+$/, ''));
      setSourceType('file');
    };
    reader.readAsText(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    readFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleFileInput = (e) => readFile(e.target.files?.[0]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-md" onClick={handleClose} />

      {/* Modal — constrained by spec: w-full max-w-2xl max-h-[90vh] overflow-y-auto */}
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-surface/95 backdrop-blur-lg border border-surface-lighter/50 rounded-2xl shadow-2xl shadow-black/40 animate-fade-in-scale">
        {/* Accent bar */}
        <div className="h-1 bg-gradient-to-r from-primary via-accent to-secondary" />

        {/* Header */}
        <div className="flex items-center justify-between px-6 sm:px-8 py-5 border-b border-surface-lighter/30 sticky top-0 bg-surface/95 backdrop-blur-lg z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/25 to-accent/15 flex items-center justify-center ring-1 ring-primary/20 flex-shrink-0">
              <Upload className="w-5 h-5 text-primary-light" />
            </div>
            <div className="min-w-0">
              <h3 className="text-base font-bold text-text-primary">Ingest Document</h3>
              <p className="text-[11px] text-text-secondary mt-0.5 truncate">
                Add knowledge to{' '}
                <span className="text-primary-light font-medium">{currentUser.name}</span>'s memory
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="w-8 h-8 rounded-xl hover:bg-surface-light/60 flex items-center justify-center transition-all cursor-pointer btn-press flex-shrink-0"
          >
            <X className="w-4 h-4 text-text-secondary" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 sm:px-8 py-6 space-y-5">
          {/* Title */}
          <div>
            <label className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary mb-2">
              <FileText className="w-3.5 h-3.5 text-text-muted/50" />
              Document Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Machine Learning Fundamentals"
              className="w-full px-4 py-2.5 bg-surface-light/50 border border-surface-lighter/50 rounded-xl text-sm text-text-primary placeholder-text-muted/40 focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 focus:bg-surface-light/70 transition-all"
              disabled={isIngesting}
            />
          </div>

          {/* Drag & drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={`flex flex-col items-center justify-center gap-3 py-8 rounded-xl border-2 border-dashed transition-all cursor-pointer ${
              isDragging
                ? 'border-primary bg-primary/10'
                : 'border-surface-lighter/50 hover:border-primary/30 hover:bg-primary/5'
            }`}
          >
            <FileUp
              className={`w-8 h-8 transition-colors ${
                isDragging ? 'text-primary-light' : 'text-text-muted/40'
              }`}
            />
            <div className="text-center">
              <p className="text-sm text-text-secondary font-medium">
                {isDragging ? 'Drop file here' : 'Drag & drop a file'}
              </p>
              <p className="text-[11px] text-text-muted/50 mt-1">
                or click to browse &bull; .txt, .md, .csv
              </p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.csv,.json,.log"
              onChange={handleFileInput}
              className="hidden"
            />
          </div>

          {/* Textarea */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
                <FileText className="w-3.5 h-3.5 text-text-muted/50" />
                Content
              </label>
              {content.length > 0 && (
                <span className="text-[10px] text-text-muted/40 font-mono">
                  {content.length} chars
                </span>
              )}
            </div>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste or type the document content here…"
              rows={8}
              className="w-full px-4 py-3 bg-surface-light/50 border border-surface-lighter/50 rounded-xl text-sm text-text-primary placeholder-text-muted/40 resize-none focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 focus:bg-surface-light/70 transition-all"
              disabled={isIngesting}
            />
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-danger/8 border border-danger/20 animate-fade-in">
              <AlertCircle className="w-4 h-4 text-danger flex-shrink-0" />
              <span className="text-xs text-danger font-medium">{error}</span>
            </div>
          )}

          {/* Success */}
          {result && (
            <div className="flex items-start gap-3 px-4 py-4 rounded-xl bg-success/8 border border-success/20 animate-fade-in">
              <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-bold text-success">Ingestion Successful!</p>
                <p className="text-xs text-text-secondary mt-1 leading-relaxed">
                  Created <strong className="text-text-primary">{result.chunks}</strong> chunks,{' '}
                  <strong className="text-text-primary">{result.nodesCreated}</strong> nodes,{' '}
                  <strong className="text-text-primary">{result.edgesCreated}</strong> edges
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 sm:px-8 py-4 border-t border-surface-lighter/30 bg-surface-light/20 sticky bottom-0">
          <button
            onClick={handleClose}
            className="px-5 py-2.5 rounded-xl text-sm text-text-secondary hover:text-text-primary hover:bg-surface-light/50 transition-all cursor-pointer btn-press font-medium"
            disabled={isIngesting}
          >
            Cancel
          </button>
          <button
            onClick={handleIngest}
            disabled={isIngesting || !title.trim() || !content.trim()}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-dark hover:from-primary-light hover:to-primary disabled:from-surface-lighter disabled:to-surface-lighter disabled:cursor-not-allowed text-white text-sm font-semibold transition-all cursor-pointer btn-press shadow-lg shadow-primary/20 disabled:shadow-none"
          >
            {isIngesting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing…
              </>
            ) : (
              <>
                <FileText className="w-4 h-4" />
                Ingest
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
