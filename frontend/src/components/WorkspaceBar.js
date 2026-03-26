import React, { useState, useEffect } from 'react';

const WorkspaceBar = ({ onSave, onLoad, currentWorkspaceId, currentWorkspaceName }) => {
  const [workspaceName, setWorkspaceName] = useState(currentWorkspaceName || '');
  const [workspaces, setWorkspaces] = useState([]);
  const [showLoadDialog, setShowLoadDialog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loadingList, setLoadingList] = useState(false);

  useEffect(() => {
    setWorkspaceName(currentWorkspaceName || '');
  }, [currentWorkspaceName]);

  const fetchWorkspaces = async () => {
    setLoadingList(true);
    try {
      const response = await fetch('/v1/workspace/list');
      if (response.ok) {
        const data = await response.json();
        setWorkspaces(data);
      }
    } catch (e) {
      console.error('Failed to fetch workspaces:', e);
    } finally {
      setLoadingList(false);
    }
  };

  const handleSave = async () => {
    const name = workspaceName.trim();
    if (!name) {
      alert('Please enter a workspace name');
      return;
    }
    setSaving(true);
    try {
      await onSave(name);
    } finally {
      setSaving(false);
    }
  };

  const handleOpenLoad = () => {
    fetchWorkspaces();
    setShowLoadDialog(true);
  };

  const handleLoad = async (workspace) => {
    setShowLoadDialog(false);
    await onLoad(workspace.id);
  };

  const handleDelete = async (e, workspaceId) => {
    e.stopPropagation();
    if (!window.confirm('Delete this workspace?')) return;
    try {
      const response = await fetch(`/v1/workspace/${workspaceId}`, { method: 'DELETE' });
      if (response.ok) {
        setWorkspaces(prev => prev.filter(w => w.id !== workspaceId));
      }
    } catch (e) {
      console.error('Failed to delete workspace:', e);
    }
  };

  const formatDate = (isoString) => {
    const d = new Date(isoString);
    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="workspace-bar">
      <div className="workspace-controls">
        <input
          type="text"
          className="workspace-name-input"
          value={workspaceName}
          onChange={(e) => setWorkspaceName(e.target.value)}
          placeholder="Workspace name"
        />
        <button
          className="workspace-btn workspace-save-btn"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button
          className="workspace-btn workspace-load-btn"
          onClick={handleOpenLoad}
        >
          Load
        </button>
      </div>

      {showLoadDialog && (
        <div className="workspace-dialog-overlay" onClick={() => setShowLoadDialog(false)}>
          <div className="workspace-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="workspace-dialog-header">
              <h3>Load Workspace</h3>
              <button className="workspace-dialog-close" onClick={() => setShowLoadDialog(false)}>X</button>
            </div>
            <div className="workspace-dialog-body">
              {loadingList && <div className="loading">Loading...</div>}
              {!loadingList && workspaces.length === 0 && (
                <div className="loading">No saved workspaces</div>
              )}
              {!loadingList && workspaces.map(w => (
                <div
                  key={w.id}
                  className={`workspace-list-item ${w.id === currentWorkspaceId ? 'active' : ''}`}
                  onClick={() => handleLoad(w)}
                >
                  <div className="workspace-list-info">
                    <div className="workspace-list-name">{w.name}</div>
                    <div className="workspace-list-date">{formatDate(w.updated_at)}</div>
                  </div>
                  <button
                    className="workspace-delete-btn"
                    onClick={(e) => handleDelete(e, w.id)}
                    title="Delete"
                  >
                    Del
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkspaceBar;
