import React, { useState, useEffect, useCallback, useRef } from 'react';
import FileUpload from './components/FileUpload';
import FileList from './components/FileList';
import ParameterPanel from './components/ParameterPanel';
import SpritePlayer from './components/SpritePlayer';
import WorkspaceBar from './components/WorkspaceBar';
import TileBackgroundRow from './components/TileBackgroundRow';
import { unzipStored } from './utils/zip';
import {
  DEFAULT_PARAMS,
  loadStoredParams,
  saveParams,
  clearStoredParams,
} from './utils/paramStorage';
import './index.css';

const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

const App = () => {
  const [sprites, setSprites] = useState([]);
  const [shadowImages, setShadowImages] = useState([]);
  const [background, setBackground] = useState(null);
  const [tileBackgrounds, setTileBackgrounds] = useState([]);
  const [selectedSpriteNames, setSelectedSpriteNames] = useState(new Set());
  // Restore whatever was used last time; falls back to defaults field by field.
  const [params, setParams] = useState(loadStoredParams);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);
  const [exportFilename, setExportFilename] = useState('atlas.png');
  const [workspaceId, setWorkspaceId] = useState(null);
  const [workspaceName, setWorkspaceName] = useState('');

  // Keep selection in sync when sprites are removed.
  useEffect(() => {
    setSelectedSpriteNames(prev => {
      const valid = new Set(sprites.map(s => s.name));
      const next = new Set();
      let changed = false;
      prev.forEach(name => {
        if (valid.has(name)) next.add(name); else changed = true;
      });
      return changed ? next : prev;
    });
  }, [sprites]);

  // Escape hatch from a remembered setup. Per-tile assignments are made from
  // the sprite list rather than the parameter panel, so they survive a reset.
  const resetParams = () => {
    setParams(p => ({
      ...DEFAULT_PARAMS,
      tileBackgroundAssignments: p.tileBackgroundAssignments,
    }));
    clearStoredParams();
  };

  const assignBackgroundToSelected = (bgFilename) => {
    if (selectedSpriteNames.size === 0) return;
    setParams(p => {
      const next = { ...(p.tileBackgroundAssignments || {}) };
      selectedSpriteNames.forEach(name => { next[name] = bgFilename; });
      return { ...p, tileBackgroundAssignments: next };
    });
  };

  const clearBackgroundFromSelected = () => {
    if (selectedSpriteNames.size === 0) return;
    setParams(p => {
      const next = { ...(p.tileBackgroundAssignments || {}) };
      selectedSpriteNames.forEach(name => { delete next[name]; });
      return { ...p, tileBackgroundAssignments: next };
    });
  };

  const removeTileBackground = (bgFilename) => {
    setTileBackgrounds(prev => prev.filter(f => f.name !== bgFilename));
    setParams(p => {
      const next = { ...(p.tileBackgroundAssignments || {}) };
      Object.keys(next).forEach(k => { if (next[k] === bgFilename) delete next[k]; });
      return { ...p, tileBackgroundAssignments: next };
    });
  };

  const debounce = (func, wait) => {
    let timeout;
    const executedFunction = function (...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
    
    executedFunction.cancel = () => {
      clearTimeout(timeout);
    };
    
    return executedFunction;
  };

  const generatePreview = useCallback(async () => {
    if (sprites.length === 0) {
      setPreviewUrl(null);
      setReport(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      
      // Add sprites
      sprites.forEach(sprite => {
        formData.append('images', sprite);
      });

      // Add shadow images if enabled
      if (params.useShadowImages && shadowImages.length > 0) {
        shadowImages.forEach(shadow => {
          formData.append('shadowImages', shadow);
        });
      }

      // Add background if enabled
      if (params.useBackground && background) {
        formData.append('background', background);
      }

      // Add per-tile background images (only those actually referenced).
      const usedBgNames = new Set(Object.values(params.tileBackgroundAssignments || {}));
      tileBackgrounds.forEach(bg => {
        if (usedBgNames.has(bg.name)) {
          formData.append('tileBackgrounds', bg);
        }
      });

      // Add parameters
      formData.append('params', JSON.stringify(params));

      const response = await fetch('/v1/atlas/preview', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Preview generation failed');
      }

      // Get report from header
      const reportHeader = response.headers.get('X-Atlas-Report');
      if (reportHeader) {
        try {
          const reportData = JSON.parse(atob(reportHeader));
          setReport(reportData);
        } catch (e) {
          console.warn('Failed to parse report:', e);
          setReport(null);
        }
      } else {
        setReport(null);
      }

      // Create preview URL
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      
      // Clean up previous URL - but don't include previewUrl in dependencies
      setPreviewUrl(prevUrl => {
        if (prevUrl) {
          URL.revokeObjectURL(prevUrl);
        }
        return url;
      });

      // The backend accepted this combination, so it is worth remembering.
      saveParams(params);
    } catch (err) {
      setError(err.message);
      setPreviewUrl(null);
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [sprites, shadowImages, background, tileBackgrounds, params]); // Remove previewUrl from dependencies

  // Create a stable debounced function
  const debouncedPreviewRef = useRef();
  
  useEffect(() => {
    // Clean up previous debounced function
    if (debouncedPreviewRef.current) {
      debouncedPreviewRef.current.cancel && debouncedPreviewRef.current.cancel();
    }
    
    // Create new debounced function
    debouncedPreviewRef.current = debounce(generatePreview, 300);
  }, [generatePreview]);

  useEffect(() => {
    if (debouncedPreviewRef.current) {
      debouncedPreviewRef.current();
    }
  }, [sprites, shadowImages, background, tileBackgrounds, params]);

  const exportAtlas = async () => {
    if (sprites.length === 0) return;

    setLoading(true);
    setError(null);

    // Ensure filename has .png extension
    let filename = exportFilename.trim();
    if (!filename) {
      filename = 'atlas.png';
    } else if (!filename.toLowerCase().endsWith('.png')) {
      filename += '.png';
    }

    try {
      const formData = new FormData();
      
      // Add sprites
      sprites.forEach(sprite => {
        formData.append('images', sprite);
      });

      // Add shadow images if enabled
      if (params.useShadowImages && shadowImages.length > 0) {
        shadowImages.forEach(shadow => {
          formData.append('shadowImages', shadow);
        });
      }

      // Add background if enabled
      if (params.useBackground && background) {
        formData.append('background', background);
      }

      // Add per-tile background images (only those actually referenced).
      const usedBgNames = new Set(Object.values(params.tileBackgroundAssignments || {}));
      tileBackgrounds.forEach(bg => {
        if (usedBgNames.has(bg.name)) {
          formData.append('tileBackgrounds', bg);
        }
      });

      // Add parameters (without preview scaling)
      const exportParams = { ...params, previewMaxWidth: Number.MAX_SAFE_INTEGER };
      formData.append('params', JSON.stringify(exportParams));
      formData.append('exportFilename', filename);

      const response = await fetch('/v1/atlas/export', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Export failed');
      }

      const blob = await response.blob();

      // Layered export arrives as an archive holding the sprite and shadow
      // sheets; save them as two files rather than handing over the zip.
      if (params.exportLayerMode === 'separate') {
        const entries = await unzipStored(blob);
        entries.forEach(entry => downloadBlob(entry.blob, entry.name));
      } else {
        downloadBlob(blob, filename);
      }

      // Persist the panel's own values, not the export overrides above.
      saveParams(params);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveWorkspace = async (name) => {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('params', JSON.stringify(params));
    formData.append('exportFilename', exportFilename);
    if (workspaceId) {
      formData.append('workspaceId', workspaceId);
    }
    sprites.forEach(sprite => formData.append('images', sprite));
    shadowImages.forEach(shadow => formData.append('shadowImages', shadow));
    if (background) {
      formData.append('background', background);
    }
    tileBackgrounds.forEach(bg => formData.append('tileBackgrounds', bg));

    const response = await fetch('/v1/workspace/save', {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json();
      setError(err.detail || 'Save failed');
      return;
    }
    const result = await response.json();
    setWorkspaceId(result.id);
    setWorkspaceName(name);
  };

  const handleLoadWorkspace = async (id) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/v1/workspace/${id}`);
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Load failed');
      }
      const data = await response.json();

      // Convert base64 images back to File objects
      const toFile = (entry) => {
        const binary = atob(entry.data);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const ext = entry.filename.split('.').pop().toLowerCase();
        const mimeTypes = { png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', gif: 'image/gif', bmp: 'image/bmp', webp: 'image/webp' };
        return new File([bytes], entry.filename, { type: mimeTypes[ext] || 'image/png' });
      };

      setSprites(data.sprites.map(toFile));
      setShadowImages(data.shadowImages.map(toFile));
      setBackground(data.background ? toFile(data.background) : null);
      setTileBackgrounds((data.tileBackgrounds || []).map(toFile));
      setSelectedSpriteNames(new Set());
      // A workspace outranks the remembered parameters; defaults only fill the
      // gaps left by workspaces saved before a parameter existed.
      setParams({ ...DEFAULT_PARAMS, ...data.params });
      setExportFilename(data.export_filename || 'atlas.png');
      setWorkspaceId(data.id);
      setWorkspaceName(data.name);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderReport = () => {
    if (!report) return null;

    return (
      <div className="report">
        {report.ignored && report.ignored.length > 0 && (
          <div className="report-section">
            <div className="report-title">Ignored ({report.ignored.length}):</div>
            <div className="report-list">
              {report.ignored.map((item, index) => (
                <div key={index}>{item.name} - {item.reason}</div>
              ))}
            </div>
          </div>
        )}
        
        {report.shadowMissing && report.shadowMissing.length > 0 && (
          <div className="report-section">
            <div className="report-title">Missing Shadows ({report.shadowMissing.length}):</div>
            <div className="report-list">
              {report.shadowMissing.map((name, index) => (
                <div key={index}>{name}</div>
              ))}
            </div>
          </div>
        )}
        
        {report.shadowAmbiguous && report.shadowAmbiguous.length > 0 && (
          <div className="report-section">
            <div className="report-title">Ambiguous Shadows ({report.shadowAmbiguous.length}):</div>
            <div className="report-list">
              {report.shadowAmbiguous.map((item, index) => (
                <div key={index}>
                  {item.sprite} → {item.candidates.join(', ')}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="app">
      <WorkspaceBar
        onSave={handleSaveWorkspace}
        onLoad={handleLoadWorkspace}
        currentWorkspaceId={workspaceId}
        currentWorkspaceName={workspaceName}
      />
      <div className="main-content">
        <div className="left-panel">
          {/* Sprites Section */}
          <div className="section">
            <h2>Sprites (Images)</h2>
            <FileUpload
              onFilesAdded={(files) => setSprites(prev => [...prev, ...files])}
            >
              {sprites.length === 0 ? (
                <p>Drag and drop sprite images here, or click to select files</p>
              ) : (
                <p>Drag and drop more images, or click to add files</p>
              )}
            </FileUpload>
            {sprites.length > 0 && (
              <FileList
                files={sprites}
                onFilesChange={setSprites}
                selectable
                selectedFilenames={selectedSpriteNames}
                onSelectionChange={setSelectedSpriteNames}
                getBadge={(file) => params.tileBackgroundAssignments?.[file.name] || null}
              />
            )}
          </div>

          {/* Shadow Images Section */}
          <div className="section">
            <h2>Shadow Images</h2>
            <FileUpload
              onFilesAdded={(files) => setShadowImages(prev => [...prev, ...files])}
            >
              {shadowImages.length === 0 ? (
                <p>Drag and drop shadow images here (optional)</p>
              ) : (
                <p>Drag and drop more shadow images</p>
              )}
            </FileUpload>
            {shadowImages.length > 0 && (
              <FileList files={shadowImages} onFilesChange={setShadowImages} />
            )}
          </div>

          {/* Background Section */}
          <div className="section">
            <h2>Background Image</h2>
            <FileUpload
              onFilesAdded={(files) => setBackground(files[0] || null)}
              multiple={false}
            >
              {background ? (
                <p>Background: {background.name}</p>
              ) : (
                <p>Drag and drop background image here (optional)</p>
              )}
            </FileUpload>
          </div>

          {/* Tile Backgrounds Section */}
          <div className="section">
            <h2>Tile Backgrounds</h2>
            <p className="hint">
              Per-sprite backgrounds. Select sprites above, then click "Assign" on a background.
              Per-tile backgrounds override the global background.
            </p>
            <FileUpload
              onFilesAdded={(files) => setTileBackgrounds(prev => {
                const existingNames = new Set(prev.map(f => f.name));
                const incoming = files.filter(f => !existingNames.has(f.name));
                return [...prev, ...incoming];
              })}
            >
              <p>Drag and drop tile background images here</p>
            </FileUpload>
            {selectedSpriteNames.size > 0 && (
              <div className="tile-bg-toolbar">
                <span>{selectedSpriteNames.size} sprite(s) selected</span>
                <button
                  type="button"
                  className="tile-bg-clear-btn"
                  onClick={clearBackgroundFromSelected}
                >
                  Clear background from selected
                </button>
              </div>
            )}
            {tileBackgrounds.length > 0 && (
              <div className="tile-bg-list">
                {tileBackgrounds.map(bg => {
                  const usageCount = Object.values(params.tileBackgroundAssignments || {})
                    .filter(v => v === bg.name).length;
                  return (
                    <TileBackgroundRow
                      key={bg.name}
                      file={bg}
                      usageCount={usageCount}
                      canAssign={selectedSpriteNames.size > 0}
                      onAssign={() => assignBackgroundToSelected(bg.name)}
                      onRemove={() => removeTileBackground(bg.name)}
                    />
                  );
                })}
              </div>
            )}
          </div>

          {/* Parameters Section */}
          <div className="section">
            <h2>Parameters</h2>
            <ParameterPanel params={params} onParamsChange={setParams} onReset={resetParams} />
          </div>
        </div>

        <div className="right-panel">
          {/* Preview Section */}
          <div className="section">
            <h2>Preview</h2>
            <div className="preview-container">
              {loading && <div className="loading">Generating preview...</div>}
              {error && <div className="error">Error: {error}</div>}
              {previewUrl && !loading && (
                <img src={previewUrl} alt="Atlas Preview" className="preview-image" />
              )}
              {!previewUrl && !loading && !error && sprites.length === 0 && (
                <div className="loading">Add some images to see preview</div>
              )}
            </div>
          </div>

          {/* Sprite Player Section */}
          <div className="section">
            <h2>Sprite Player</h2>
            <SpritePlayer
              previewUrl={previewUrl}
              tileSize={params.tileSize}
              columns={params.width}
            />
          </div>

          {/* Report Section */}
          {renderReport()}

          {/* Export Section */}
          <div className="section">
            <h2>Export</h2>
            <div className="param-item">
              <label>File Name</label>
              <input
                type="text"
                value={exportFilename}
                onChange={(e) => setExportFilename(e.target.value)}
                placeholder="atlas.png"
              />
            </div>
            <div className="param-item">
              <label htmlFor="export-layer-mode">Layers</label>
              <select
                id="export-layer-mode"
                value={params.exportLayerMode}
                onChange={(e) => setParams(p => ({ ...p, exportLayerMode: e.target.value }))}
              >
                <option value="separate">Separate sprite &amp; shadow sheets</option>
                <option value="combined">Single merged sheet</option>
              </select>
            </div>
            <p className="hint">
              {params.exportLayerMode === 'separate' ? (
                <>
                  Exports two aligned sheets: the sprites, and a
                  {' '}<code>_shadow</code> sheet carrying the shadows
                  {' '}<strong>and the backgrounds</strong>. The preview above always
                  shows them merged.
                </>
              ) : (
                'Exports one sheet with sprites, shadows and backgrounds merged.'
              )}
            </p>
            <button
              className="export-button"
              onClick={exportAtlas}
              disabled={loading || sprites.length === 0}
            >
              {loading ? 'Processing...' : 'Export Atlas'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;