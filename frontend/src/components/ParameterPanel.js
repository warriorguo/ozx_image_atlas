import React from 'react';

const ParameterPanel = ({ params, onParamsChange }) => {
  const updateParam = (key, value) => {
    onParamsChange({ ...params, [key]: value });
  };

  return (
    <div className="param-grid">
      <div className="param-item">
        <label>Tile Size</label>
        <input
          type="number"
          value={params.tileSize}
          onChange={(e) => updateParam('tileSize', parseInt(e.target.value) || 52)}
          min="1"
          max="512"
        />
      </div>

      <div className="param-item">
        <label>Width (tiles)</label>
        <input
          type="number"
          value={params.width}
          onChange={(e) => updateParam('width', parseInt(e.target.value) || 6)}
          min="1"
          max="20"
        />
      </div>

      <div className="param-item">
        <label>Sample Rate</label>
        <input
          type="number"
          value={params.sample}
          onChange={(e) => updateParam('sample', parseInt(e.target.value) || 1)}
          min="1"
        />
      </div>

      <div className="param-item">
        <label>Outline Width</label>
        <input
          type="number"
          value={params.outline}
          onChange={(e) => updateParam('outline', parseInt(e.target.value) || 0)}
          min="0"
          max="50"
        />
      </div>

      <div className="param-item">
        <label>Remove Color (hex)</label>
        <input
          type="text"
          value={params.removeColor || ''}
          onChange={(e) => updateParam('removeColor', e.target.value || null)}
          placeholder="ff0000"
        />
      </div>

      <div className="param-item">
        <label>Shadow Scale</label>
        <input
          type="number"
          step="0.1"
          value={params.shadowScale}
          onChange={(e) => updateParam('shadowScale', parseFloat(e.target.value) || 0)}
          min="0"
          max="5"
          disabled={params.useShadowImages}
        />
      </div>

      <div className="param-item checkbox-param">
        <input
          type="checkbox"
          checked={params.useShadowImages}
          onChange={(e) => updateParam('useShadowImages', e.target.checked)}
        />
        <label>Use Shadow Images</label>
      </div>

      <div className="param-item">
        <label>Missing Shadow Policy</label>
        <select
          value={params.missingShadowPolicy}
          onChange={(e) => updateParam('missingShadowPolicy', e.target.value)}
          disabled={!params.useShadowImages}
        >
          <option value="skipShadow">Skip Shadow</option>
          <option value="ignoreSprite">Ignore Sprite</option>
          <option value="fail">Fail</option>
        </select>
      </div>

      <div className="param-item checkbox-param">
        <input
          type="checkbox"
          checked={params.useBackground}
          onChange={(e) => updateParam('useBackground', e.target.checked)}
        />
        <label>Use Background</label>
      </div>

      <div className="param-item">
        <label>Preview Max Width</label>
        <input
          type="number"
          value={params.previewMaxWidth}
          onChange={(e) => updateParam('previewMaxWidth', parseInt(e.target.value) || 1024)}
          min="256"
          max="4096"
        />
      </div>
    </div>
  );
};

export default ParameterPanel;