import React, { useState, useEffect, useCallback, useRef } from 'react';
import FileUpload from './components/FileUpload';
import FileList from './components/FileList';
import ParameterPanel from './components/ParameterPanel';
import './index.css';

const App = () => {
  const [sprites, setSprites] = useState([]);
  const [shadowImages, setShadowImages] = useState([]);
  const [background, setBackground] = useState(null);
  const [params, setParams] = useState({
    tileSize: 52,
    width: 6,
    sample: 1,
    outline: 0,
    removeColor: null,
    shadowScale: 0.0,
    useShadowImages: false,
    missingShadowPolicy: 'skipShadow',
    useBackground: false,
    previewMaxWidth: 1024
  });
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);
  const [exportFilename, setExportFilename] = useState('atlas.png');

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
    } catch (err) {
      setError(err.message);
      setPreviewUrl(null);
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [sprites, shadowImages, background, params]); // Remove previewUrl from dependencies

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
  }, [sprites, shadowImages, background, params]);

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

      // Add parameters (without preview scaling)
      const exportParams = { ...params, previewMaxWidth: Number.MAX_SAFE_INTEGER };
      formData.append('params', JSON.stringify(exportParams));

      const response = await fetch('/v1/atlas/export', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Export failed');
      }

      // Download the file
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
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
              <FileList files={sprites} onFilesChange={setSprites} />
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

          {/* Parameters Section */}
          <div className="section">
            <h2>Parameters</h2>
            <ParameterPanel params={params} onParamsChange={setParams} />
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