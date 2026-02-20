import { useState } from 'react';
import { X, Upload, FileText, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import useAppStore from '../store/useAppStore';

export default function IngestModal() {
  const { isIngestModalOpen, closeIngestModal, ingestDocument, isIngesting, getCurrentUser } = useAppStore();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const currentUser = getCurrentUser();

  if (!isIngestModalOpen) return null;

  const handleIngest = async () => {
    if (!title.trim() || !content.trim()) {
      setError('Both title and content are required.');
      return;
    }
    setError('');
    try {
      const res = await ingestDocument(title.trim(), content.trim());
      setResult(res);
      setTimeout(() => {
        setTitle('');
        setContent('');
        setResult(null);
      }, 500);
    } catch (err) {
      setError('Ingestion failed. Please try again.');
    }
  };

  const handleClose = () => {
    setTitle('');
    setContent('');
    setResult(null);
    setError('');
    closeIngestModal();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={handleClose} />

      {/* Modal */}
      <div className="relative w-full max-w-lg bg-surface border border-surface-lighter rounded-2xl shadow-2xl animate-fade-in overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-lighter">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center">
              <Upload className="w-5 h-5 text-primary-light" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-text-primary">Ingest Document</h3>
              <p className="text-xs text-text-secondary">Add knowledge to {currentUser.name}'s memory</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="w-8 h-8 rounded-lg hover:bg-surface-light flex items-center justify-center transition-colors cursor-pointer"
          >
            <X className="w-4 h-4 text-text-secondary" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {/* Title input */}
          <div>
            <label className="block text-xs font-semibold text-text-secondary mb-1.5">Document Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Machine Learning Fundamentals"
              className="w-full px-3 py-2.5 bg-surface-light border border-surface-lighter rounded-xl text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all"
              disabled={isIngesting}
            />
          </div>

          {/* Content textarea */}
          <div>
            <label className="block text-xs font-semibold text-text-secondary mb-1.5">Content</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste or type the document content here..."
              rows={6}
              className="w-full px-3 py-2.5 bg-surface-light border border-surface-lighter rounded-xl text-sm text-text-primary placeholder-text-muted resize-none focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all"
              disabled={isIngesting}
            />
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-danger/10 border border-danger/20">
              <AlertCircle className="w-4 h-4 text-danger flex-shrink-0" />
              <span className="text-xs text-danger">{error}</span>
            </div>
          )}

          {/* Success */}
          {result && (
            <div className="flex items-start gap-3 px-3 py-3 rounded-lg bg-success/10 border border-success/20 animate-fade-in">
              <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-success">Ingestion Successful!</p>
                <p className="text-xs text-text-secondary mt-1">
                  Created {result.chunks} chunks, {result.nodesCreated} nodes, {result.edgesCreated} edges
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-surface-lighter">
          <button
            onClick={handleClose}
            className="px-4 py-2 rounded-xl text-sm text-text-secondary hover:text-text-primary hover:bg-surface-light transition-all cursor-pointer"
            disabled={isIngesting}
          >
            Cancel
          </button>
          <button
            onClick={handleIngest}
            disabled={isIngesting || !title.trim() || !content.trim()}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-primary hover:bg-primary-light disabled:bg-surface-lighter disabled:cursor-not-allowed text-white text-sm font-medium transition-all cursor-pointer"
          >
            {isIngesting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing...
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
