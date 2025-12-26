import { render, screen } from '@testing-library/react';
import App from '../App';

// Mock FileUpload and ParameterPanel to avoid dropzone issues in tests
jest.mock('../components/FileUpload', () => {
  return function MockFileUpload({ children, onFilesAdded, multiple }) {
    return (
      <div data-testid="file-upload">
        {children}
        <input
          type="file"
          multiple={multiple}
          onChange={(e) => onFilesAdded(Array.from(e.target.files))}
          data-testid="file-input"
        />
      </div>
    );
  };
});

jest.mock('../components/ParameterPanel', () => {
  return function MockParameterPanel({ params, onParamsChange }) {
    return (
      <div data-testid="parameter-panel">
        <input
          data-testid="tile-size"
          type="number"
          value={params.tileSize}
          onChange={(e) => onParamsChange({ ...params, tileSize: parseInt(e.target.value) })}
        />
      </div>
    );
  };
});

jest.mock('../components/FileList', () => {
  return function MockFileList({ files, onFilesChange }) {
    return (
      <div data-testid="file-list">
        {files.map((file, index) => (
          <div key={index}>{file.name}</div>
        ))}
      </div>
    );
  };
});

describe('App', () => {
  test('renders without main title', () => {
    render(<App />);
    expect(screen.queryByText('OZX Image Atlas Tool')).not.toBeInTheDocument();
  });

  test('renders all main sections', () => {
    render(<App />);
    
    expect(screen.getByText('Sprites (Images)')).toBeInTheDocument();
    expect(screen.getByText('Shadow Images')).toBeInTheDocument();
    expect(screen.getByText('Background Image')).toBeInTheDocument();
    expect(screen.getByText('Parameters')).toBeInTheDocument();
    expect(screen.getByText('Preview')).toBeInTheDocument();
    expect(screen.getByText('Export')).toBeInTheDocument();
  });

  test('export button is disabled when no images are loaded', () => {
    render(<App />);
    
    const exportButton = screen.getByRole('button', { name: /export atlas/i });
    expect(exportButton).toBeDisabled();
  });

  test('renders filename input for export', () => {
    render(<App />);
    
    const filenameInput = screen.getByDisplayValue('atlas.png');
    expect(filenameInput).toBeInTheDocument();
    expect(filenameInput).toHaveAttribute('placeholder', 'atlas.png');
  });

  test('shows appropriate message when no images are loaded', () => {
    render(<App />);
    
    expect(screen.getByText('Add some images to see preview')).toBeInTheDocument();
  });

  test('renders file upload components', () => {
    render(<App />);
    
    const fileUploads = screen.getAllByTestId('file-upload');
    expect(fileUploads).toHaveLength(3); // Sprites, Shadow, Background
  });

  test('renders parameter panel', () => {
    render(<App />);
    
    expect(screen.getByTestId('parameter-panel')).toBeInTheDocument();
  });

  test('has correct initial parameter values', () => {
    render(<App />);
    
    const tileSizeInput = screen.getByTestId('tile-size');
    expect(tileSizeInput).toHaveValue(52);
  });
});