import React, { useState, useEffect, useRef } from 'react';

const FileList = ({
  files,
  onFilesChange,
  selectable = false,
  selectedFilenames = null,
  onSelectionChange = null,
  getBadge = null,
}) => {
  const [fileStates, setFileStates] = useState([]);
  const processedFilesRef = useRef(new Set());
  const lastClickedIndexRef = useRef(null);

  useEffect(() => {
    const newFileStates = files.map((file, index) => ({
      id: index,
      file,
      enabled: true,
      thumbnail: null
    }));
    setFileStates(newFileStates);

    // Clear processed files when files change
    processedFilesRef.current = new Set();
  }, [files]);

  useEffect(() => {
    // Create thumbnails for files without thumbnails
    fileStates.forEach((fileState, index) => {
      if (!fileState.thumbnail && fileState.file) {
        // Use file name and size as unique key to avoid reprocessing
        const fileKey = `${fileState.file.name}-${fileState.file.size}`;
        if (!processedFilesRef.current.has(fileKey)) {
          processedFilesRef.current.add(fileKey);

          const reader = new FileReader();
          reader.onload = (e) => {
            setFileStates(prev => prev.map((fs, i) =>
              i === index && fs.file === fileState.file
                ? { ...fs, thumbnail: e.target.result }
                : fs
            ));
          };
          reader.readAsDataURL(fileState.file);
        }
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileStates.length]); // Only trigger when number of files changes, intentionally not including fileStates to avoid infinite loop

  const toggleFile = (index) => {
    setFileStates(prev => {
      const newStates = prev.map((fs, i) =>
        i === index ? { ...fs, enabled: !fs.enabled } : fs
      );
      onFilesChange(newStates.filter(fs => fs.enabled).map(fs => fs.file));
      return newStates;
    });
  };

  const moveFile = (fromIndex, toIndex) => {
    setFileStates(prev => {
      const newStates = [...prev];
      const [movedItem] = newStates.splice(fromIndex, 1);
      newStates.splice(toIndex, 0, movedItem);
      onFilesChange(newStates.filter(fs => fs.enabled).map(fs => fs.file));
      return newStates;
    });
  };

  const handleRowClick = (e, index, filename) => {
    if (!selectable || !onSelectionChange) return;
    const current = new Set(selectedFilenames || []);
    if (e.shiftKey && lastClickedIndexRef.current !== null) {
      const [start, end] = [lastClickedIndexRef.current, index].sort((a, b) => a - b);
      // Decide whether to select or deselect the range based on the anchor's state.
      const anchorName = fileStates[lastClickedIndexRef.current]?.file?.name;
      const select = anchorName ? current.has(anchorName) : true;
      for (let i = start; i <= end; i++) {
        const name = fileStates[i]?.file?.name;
        if (!name) continue;
        if (select) current.add(name); else current.delete(name);
      }
    } else {
      if (current.has(filename)) current.delete(filename); else current.add(filename);
      lastClickedIndexRef.current = index;
    }
    onSelectionChange(current);
  };

  const clearSelection = () => {
    if (onSelectionChange) onSelectionChange(new Set());
    lastClickedIndexRef.current = null;
  };

  const selectAll = () => {
    if (!onSelectionChange) return;
    onSelectionChange(new Set(fileStates.map(fs => fs.file.name)));
  };

  const selectedCount = selectable && selectedFilenames ? selectedFilenames.size : 0;

  return (
    <div>
      {selectable && (
        <div className="file-list-selection-bar">
          <span>{selectedCount} selected</span>
          <button type="button" className="file-list-link-btn" onClick={selectAll}>Select all</button>
          <button type="button" className="file-list-link-btn" onClick={clearSelection} disabled={selectedCount === 0}>Clear</button>
        </div>
      )}
      <div className="file-list">
        {fileStates.map((fileState, index) => {
          const filename = fileState.file.name;
          const isSelected = selectable && selectedFilenames && selectedFilenames.has(filename);
          const badge = getBadge ? getBadge(fileState.file) : null;
          const classes = [
            'file-item',
            !fileState.enabled ? 'disabled' : '',
            isSelected ? 'selected' : '',
            selectable ? 'selectable' : '',
          ].filter(Boolean).join(' ');
          return (
            <div
              key={fileState.id}
              className={classes}
              onClick={(e) => {
                // Ignore clicks originating on the checkbox or drag handle.
                if (e.target.closest('.file-toggle') || e.target.closest('.drag-handle')) return;
                handleRowClick(e, index, filename);
              }}
            >
              <span
                className="drag-handle"
                draggable
                onDragStart={(e) => e.dataTransfer.setData('text/plain', index)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  const fromIndex = parseInt(e.dataTransfer.getData('text/plain'));
                  moveFile(fromIndex, index);
                }}
              >
                ⋮⋮
              </span>
              {fileState.thumbnail && (
                <img
                  src={fileState.thumbnail}
                  alt={fileState.file.name}
                  className="file-thumbnail"
                />
              )}
              <span className="file-name">{fileState.file.name}</span>
              {badge && <span className="file-badge" title={`Tile background: ${badge}`}>BG</span>}
              <input
                type="checkbox"
                checked={fileState.enabled}
                onChange={() => toggleFile(index)}
                className="file-toggle"
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default FileList;