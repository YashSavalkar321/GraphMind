import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Upload, FileText, Loader2, CheckCircle2, AlertCircle, FileUp } from 'lucide-react';
import useAppStore from '../store/useAppStore';

export default function IngestModal() {
  const isIngestModalOpen = useAppStore((s) => s.isIngestModalOpen);
  const closeIngestModal = useAppStore((s) => s.closeIngestModal);
  const ingestDocument = useAppStore((s) => s.ingestDocument);
  const isIngesting = useAppStore((s) => s.isIngesting);
  const currentUser = useAppStore((s) => s.getCurrentUser());

  const uploadFile = useAppStore((s) => s.uploadFile);

  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [sourceType, setSourceType] = useState('text');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [pendingFile, setPendingFile] = useState(null);
  const fileInputRef = useRef(null);

  /* ── Submit ── */
  const handleIngest = async () => {
    // PDF / binary file path — upload via /upload
    if (pendingFile) {
      if (!title.trim()) {
        setError('A document title is required.');
        return;
      }
      setError('');
      try {
        const res = await uploadFile(pendingFile);
        setResult(res);
        setTimeout(() => {
          setTitle('');
          setContent('');
          setPendingFile(null);
          setResult(null);
          setSourceType('text');
        }, 600);
      } catch (err) {
        setError(err.message || 'File upload failed. Please try again.');
      }
      return;
    }

    // Text path — ingest via /memory/ingest
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
    setPendingFile(null);
    setResult(null);
    setError('');
    setSourceType('text');
    closeIngestModal();
  };

  /* ── Drag & drop / file read helpers ── */
  const BINARY_EXTS = ['pdf'];

  const readFile = (file) => {
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    if (!title.trim()) setTitle(file.name.replace(/\.[^.]+$/, ''));
    setSourceType('file');

    // Binary files (PDF) — store the File object for upload
    if (BINARY_EXTS.includes(ext)) {
      setPendingFile(file);
      setContent(`[PDF file selected: ${file.name} — ${(file.size / 1024).toFixed(1)} KB]`);
      return;
    }

    // Text-based files — read into textarea
    setPendingFile(null);
    const reader = new FileReader();
    reader.onload = (e) => {
      setContent(e.target.result);
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
    <AnimatePresence>
      {isIngestModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="absolute inset-0 bg-black/70 backdrop-blur-md"
            onClick={handleClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.93, y: 18 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 10 }}
            transition={{ type: 'spring', stiffness: 300, damping: 26 }}
            className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto glass-strong rounded-3xl"
          >
            {/* Animated accent bar */}
            <div className="h-1 gradient-bar" />

            {/* Header */}
            <div className="flex items-center justify-between px-6 sm:px-8 py-5 border-b border-white/[0.06] sticky top-0 glass-strong !border-x-0 !border-t-0 !shadow-none z-10">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-primary/30 via-accent/20 to-transparent flex items-center justify-center ring-1 ring-primary/25 flex-shrink-0 shadow-[0_0_18px_rgba(99,102,241,0.25)]">
                  <Upload className="w-5 h-5 text-primary-light" />
                </div>
                <div className="min-w-0">
                  <h3 className="font-display text-base font-bold text-text-primary">Ingest Knowledge</h3>
                  <p className="text-[11px] text-text-secondary mt-0.5 truncate">
                    Feed{' '}
                    <span className="text-primary-light font-medium">{currentUser?.name || 'Guest'}</span>
                    's memory graph
                  </p>
                </div>
              </div>
              <button
                onClick={handleClose}
                className="w-8 h-8 rounded-xl hover:bg-white/[0.07] flex items-center justify-center transition-all cursor-pointer btn-press flex-shrink-0"
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
                  className="w-full px-4 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-xl text-sm text-text-primary placeholder-text-muted/40 focus:outline-none focus:border-primary/50 focus:bg-white/[0.06] focus:shadow-[0_0_0_3px_rgba(99,102,241,0.12)] transition-all"
                  disabled={isIngesting}
                />
              </div>

              {/* Drag & drop zone */}
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
                className={`relative flex flex-col items-center justify-center gap-3 py-8 rounded-2xl border-2 border-dashed transition-all cursor-pointer overflow-hidden ${
                  isDragging
                    ? 'border-primary bg-primary/10 shadow-[inset_0_0_40px_rgba(99,102,241,0.15)] scale-[1.01]'
                    : 'border-white/[0.1] hover:border-primary/40 hover:bg-primary/5'
                }`}
              >
                <div
                  className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-all ${
                    isDragging
                      ? 'bg-primary/20 scale-110'
                      : 'bg-white/[0.04]'
                  }`}
                >
                  <FileUp
                    className={`w-6 h-6 transition-colors ${
                      isDragging ? 'text-primary-light' : 'text-text-muted/50'
                    }`}
                  />
                </div>
                <div className="text-center">
                  <p className="text-sm text-text-secondary font-medium">
                    {isDragging ? 'Drop it — I’ll remember it' : 'Drag & drop a file'}
                  </p>
                  <p className="text-[11px] text-text-muted/50 mt-1">
                    or click to browse &bull; .pdf, .txt, .md, .csv
                  </p>
                </div>
                {pendingFile && (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-primary/12 border border-primary/30 shadow-[0_0_14px_rgba(99,102,241,0.2)]">
                    <FileText className="w-4 h-4 text-primary-light" />
                    <span className="text-xs text-primary-light font-medium truncate max-w-[200px]">
                      {pendingFile.name}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setPendingFile(null); setContent(''); setSourceType('text'); }}
                      className="ml-1 w-5 h-5 rounded-full hover:bg-white/[0.1] flex items-center justify-center"
                    >
                      <X className="w-3 h-3 text-text-muted" />
                    </button>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.txt,.md,.csv,.json,.log"
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
                  className="w-full px-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-xl text-sm text-text-primary placeholder-text-muted/40 resize-none focus:outline-none focus:border-primary/50 focus:bg-white/[0.06] focus:shadow-[0_0_0_3px_rgba(99,102,241,0.12)] transition-all"
                  disabled={isIngesting}
                />
              </div>

              {/* Error */}
              {error && (
                <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-danger/10 border border-danger/25 animate-fade-in">
                  <AlertCircle className="w-4 h-4 text-danger flex-shrink-0" />
                  <span className="text-xs text-danger font-medium">{error}</span>
                </div>
              )}

              {/* Success */}
              {result && (
                <div className="flex items-start gap-3 px-4 py-4 rounded-xl bg-success/10 border border-success/25 shadow-[0_0_20px_rgba(52,211,153,0.12)] animate-fade-in">
                  <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-bold text-success">Memory absorbed!</p>
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
            <div className="flex items-center justify-end gap-3 px-6 sm:px-8 py-4 border-t border-white/[0.06] sticky bottom-0 glass-strong !border-x-0 !border-b-0 !shadow-none">
              <button
                onClick={handleClose}
                className="px-5 py-2.5 rounded-xl text-sm text-text-secondary hover:text-text-primary hover:bg-white/[0.05] transition-all cursor-pointer btn-press font-medium"
                disabled={isIngesting}
              >
                Cancel
              </button>
              <button
                onClick={handleIngest}
                disabled={isIngesting || !title.trim() || (!content.trim() && !pendingFile)}
                className="sheen flex items-center gap-2 px-6 py-2.5 rounded-xl btn-glow text-white text-sm font-bold cursor-pointer"
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
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
