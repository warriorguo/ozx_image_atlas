import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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
describe('App export layer mode', () => {
  test('defaults to separate sprite and shadow sheets', () => {
    render(<App />);

    const layerSelect = screen.getByLabelText('Layers');
    expect(layerSelect).toHaveValue('separate');
    expect(screen.getByText(/_shadow/)).toBeInTheDocument();
  });

  test('switching to combined explains the merged output', async () => {
    render(<App />);

    const layerSelect = screen.getByLabelText('Layers');
    fireEvent.change(layerSelect, { target: { value: 'combined' } });

    expect(layerSelect).toHaveValue('combined');
    expect(screen.getByText(/one sheet with sprites, shadows and backgrounds merged/i))
      .toBeInTheDocument();
  });
});

describe('App export downloads', () => {
  // ZIP_STORED archive holding atlas.png and atlas_shadow.png (see zip.test.js).
  const ZIP_FIXTURE =
    'UEsDBBQAAAAAAEFY/FzR+0LpDAAAAAwAAAAJAAAAYXRsYXMucG5nc3ByaXRlLWJ5dGVzUEsDBBQAAAAAAEFY' +
    '/FzCkA+ODgAAAA4AAAAQAAAAYXRsYXNfc2hhZG93LnBuZ3NoYWRvdy1ieXRlcy14UEsBAhQDFAAAAAAAQVj8' +
    'XNH7QukMAAAADAAAAAkAAAAAAAAAAAAAAIABAAAAAGF0bGFzLnBuZ1BLAQIUAxQAAAAAAEFY/FzCkA+ODgAA' +
    'AA4AAAAQAAAAAAAAAAAAAACAATMAAABhdGxhc19zaGFkb3cucG5nUEsFBgAAAAACAAIAdQAAAG8AAAAAAA==';

  const zipBlob = () => {
    const binary = atob(ZIP_FIXTURE);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes]);
    blob.arrayBuffer = () => Promise.resolve(bytes.buffer);
    return blob;
  };

  let downloads;

  beforeEach(() => {
    downloads = [];
    global.URL.createObjectURL = jest.fn(() => 'blob:mock');
    global.URL.revokeObjectURL = jest.fn();
    jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
      downloads.push(this.download);
    });
    global.fetch = jest.fn((url) => Promise.resolve({
      ok: true,
      headers: { get: () => null },
      blob: () => Promise.resolve(
        String(url).includes('export') ? zipBlob() : new Blob(['png'])),
    }));
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('separate mode saves the sprite sheet and the shadow sheet', async () => {
    render(<App />);

    const [spriteInput] = screen.getAllByTestId('file-input');
    fireEvent.change(spriteInput, {
      target: { files: [new File(['x'], 'hero.png', { type: 'image/png' })] },
    });

    fireEvent.click(screen.getByRole('button', { name: /export atlas/i }));

    await waitFor(() => expect(downloads).toEqual(['atlas.png', 'atlas_shadow.png']));

    const exportCall = global.fetch.mock.calls.find(([url]) => String(url).includes('export'));
    const sentParams = JSON.parse(exportCall[1].body.get('params'));
    expect(sentParams.exportLayerMode).toBe('separate');
    expect(exportCall[1].body.get('exportFilename')).toBe('atlas.png');
  });

  test('combined mode saves a single file', async () => {
    render(<App />);

    const [spriteInput] = screen.getAllByTestId('file-input');
    fireEvent.change(spriteInput, {
      target: { files: [new File(['x'], 'hero.png', { type: 'image/png' })] },
    });
    fireEvent.change(screen.getByLabelText('Layers'), { target: { value: 'combined' } });

    fireEvent.click(screen.getByRole('button', { name: /export atlas/i }));

    await waitFor(() => expect(downloads).toEqual(['atlas.png']));
  });
});
