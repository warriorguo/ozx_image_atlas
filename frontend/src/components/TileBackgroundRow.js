import React, { useEffect, useState } from 'react';

const TileBackgroundRow = ({ file, usageCount, canAssign, onAssign, onRemove }) => {
  const [thumbnail, setThumbnail] = useState(null);

  useEffect(() => {
    const reader = new FileReader();
    reader.onload = (e) => setThumbnail(e.target.result);
    reader.readAsDataURL(file);
  }, [file]);

  return (
    <div className="tile-bg-item">
      {thumbnail && <img src={thumbnail} alt={file.name} className="tile-bg-thumb" />}
      <div className="tile-bg-info">
        <div className="tile-bg-name">{file.name}</div>
        <div className="tile-bg-usage">
          {usageCount === 0 ? 'unused' : `applied to ${usageCount} sprite(s)`}
        </div>
      </div>
      <button
        type="button"
        className="tile-bg-assign-btn"
        onClick={onAssign}
        disabled={!canAssign}
        title={canAssign ? 'Assign to selected sprites' : 'Select sprites first'}
      >
        Assign
      </button>
      <button
        type="button"
        className="tile-bg-remove-btn"
        onClick={onRemove}
        title="Remove this background"
      >
        ×
      </button>
    </div>
  );
};

export default TileBackgroundRow;
