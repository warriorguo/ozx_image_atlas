import { render, screen } from '@testing-library/react';
import FileUpload from '../FileUpload';

describe('FileUpload', () => {
  const mockOnFilesAdded = jest.fn();

  beforeEach(() => {
    mockOnFilesAdded.mockClear();
  });

  test('renders with children', () => {
    render(
      <FileUpload onFilesAdded={mockOnFilesAdded}>
        <p>Drop files here</p>
      </FileUpload>
    );

    expect(screen.getByText('Drop files here')).toBeInTheDocument();
  });

  test('has proper dropzone attributes', () => {
    render(
      <FileUpload onFilesAdded={mockOnFilesAdded}>
        <p>Drop files here</p>
      </FileUpload>
    );

    const dropzone = screen.getByText('Drop files here').closest('div');
    expect(dropzone).toHaveClass('dropzone');
  });

  test('accepts multiple files by default', () => {
    render(
      <FileUpload onFilesAdded={mockOnFilesAdded}>
        <p>Drop files here</p>
      </FileUpload>
    );

    const input = document.querySelector('input[type="file"]');
    expect(input).toHaveAttribute('multiple');
  });

  test('can be configured for single file', () => {
    render(
      <FileUpload onFilesAdded={mockOnFilesAdded} multiple={false}>
        <p>Drop files here</p>
      </FileUpload>
    );

    const input = document.querySelector('input[type="file"]');
    expect(input).not.toHaveAttribute('multiple');
  });
});