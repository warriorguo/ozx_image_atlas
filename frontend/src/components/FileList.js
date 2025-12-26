import React, { useState, useEffect, useRef } from 'react';

const FileList = ({ files, onFilesChange }) => {
  const [fileStates, setFileStates] = useState([]);
  const processedFilesRef = useRef(new Set());

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

  return (
    <div className="file-list">
      {fileStates.map((fileState, index) => (
        <div 
          key={fileState.id} 
          className={`file-item ${!fileState.enabled ? 'disabled' : ''}`}
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
          <input
            type="checkbox"
            checked={fileState.enabled}
            onChange={() => toggleFile(index)}
            className="file-toggle"
          />
        </div>
      ))}
    </div>
  );
};

export default FileList;