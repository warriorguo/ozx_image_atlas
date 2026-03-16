import React, { useState, useEffect, useRef, useCallback } from 'react';

const SpritePlayer = ({ previewUrl, tileSize, columns }) => {
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  const animFrameRef = useRef(null);
  const lastFrameTimeRef = useRef(0);
  const currentFrameRef = useRef(0);
  const tileSizeInPreviewRef = useRef({ w: 0, h: 0 });

  const [startFrame, setStartFrame] = useState(0);
  const [endFrame, setEndFrame] = useState(0);
  const [fps, setFps] = useState(30);
  const [loop, setLoop] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [totalTiles, setTotalTiles] = useState(0);
  const [imageLoaded, setImageLoaded] = useState(false);

  // Load image and calculate total tiles from actual image dimensions
  useEffect(() => {
    if (!previewUrl) {
      setImageLoaded(false);
      setTotalTiles(0);
      return;
    }

    const img = new Image();
    img.onload = () => {
      imageRef.current = img;
      const cols = columns || 1;
      // Calculate actual tile size in the preview image from image dimensions
      const tileW = img.width / cols;
      const tileH = tileW; // tiles are square
      tileSizeInPreviewRef.current = { w: tileW, h: tileH };
      const rows = Math.round(img.height / tileH) || 1;
      const total = cols * rows;
      setTotalTiles(total);
      setEndFrame(total - 1);
      setImageLoaded(true);
    };
    img.src = previewUrl;
  }, [previewUrl, tileSize, columns]);

  const drawFrame = useCallback((frameIndex) => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img) return;

    const { w: tileW, h: tileH } = tileSizeInPreviewRef.current;
    if (tileW <= 0 || tileH <= 0) return;

    const ctx = canvas.getContext('2d');
    canvas.width = tileW;
    canvas.height = tileH;

    const col = frameIndex % columns;
    const row = Math.floor(frameIndex / columns);
    const sx = col * tileW;
    const sy = row * tileH;

    ctx.clearRect(0, 0, tileW, tileH);
    ctx.drawImage(img, sx, sy, tileW, tileH, 0, 0, tileW, tileH);
  }, [columns]);

  // Animation loop
  useEffect(() => {
    if (!playing || !imageLoaded) return;

    const frameDuration = 1000 / fps;
    currentFrameRef.current = startFrame;
    lastFrameTimeRef.current = 0;
    drawFrame(startFrame);

    const animate = (timestamp) => {
      if (!lastFrameTimeRef.current) {
        lastFrameTimeRef.current = timestamp;
      }

      const elapsed = timestamp - lastFrameTimeRef.current;

      if (elapsed >= frameDuration) {
        lastFrameTimeRef.current = timestamp - (elapsed % frameDuration);
        currentFrameRef.current++;

        if (currentFrameRef.current > endFrame) {
          if (loop) {
            currentFrameRef.current = startFrame;
          } else {
            setPlaying(false);
            return;
          }
        }

        drawFrame(currentFrameRef.current);
      }

      animFrameRef.current = requestAnimationFrame(animate);
    };

    animFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [playing, startFrame, endFrame, fps, loop, imageLoaded, drawFrame]);

  // Draw first frame when not playing but params change
  useEffect(() => {
    if (!playing && imageLoaded) {
      drawFrame(startFrame);
    }
  }, [startFrame, imageLoaded, playing, drawFrame]);

  if (!previewUrl) return null;

  const maxFrame = totalTiles > 0 ? totalTiles - 1 : 0;
  const displaySize = Math.min(tileSize * 2, 256);

  return (
    <div className="sprite-player">
      <div className="sprite-player-canvas">
        <canvas
          ref={canvasRef}
          style={{
            width: displaySize,
            height: displaySize,
            imageRendering: 'pixelated',
            border: '1px solid #ddd',
            borderRadius: '4px',
            background: '#f0f0f0'
          }}
        />
      </div>

      <div className="param-grid">
        <div className="param-item">
          <label>Start Frame</label>
          <input
            type="number"
            value={startFrame}
            onChange={(e) => {
              const v = Math.max(0, Math.min(parseInt(e.target.value) || 0, maxFrame));
              setStartFrame(v);
            }}
            min="0"
            max={maxFrame}
          />
        </div>

        <div className="param-item">
          <label>End Frame</label>
          <input
            type="number"
            value={endFrame}
            onChange={(e) => {
              const v = Math.max(0, Math.min(parseInt(e.target.value) || 0, maxFrame));
              setEndFrame(v);
            }}
            min="0"
            max={maxFrame}
          />
        </div>

        <div className="param-item">
          <label>FPS</label>
          <input
            type="number"
            value={fps}
            onChange={(e) => setFps(Math.max(1, Math.min(parseInt(e.target.value) || 30, 120)))}
            min="1"
            max="120"
          />
        </div>

        <div className="param-item checkbox-param">
          <input
            type="checkbox"
            checked={loop}
            onChange={(e) => setLoop(e.target.checked)}
          />
          <label>Loop</label>
        </div>
      </div>

      <button
        className="play-button"
        onClick={() => setPlaying(!playing)}
        disabled={!imageLoaded || totalTiles === 0}
      >
        {playing ? 'Stop' : 'Play'}
      </button>
    </div>
  );
};

export default SpritePlayer;
