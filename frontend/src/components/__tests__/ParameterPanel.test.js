import { render, screen, fireEvent } from '@testing-library/react';
import ParameterPanel from '../ParameterPanel';

describe('ParameterPanel', () => {
  const defaultParams = {
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
  };

  const mockOnParamsChange = jest.fn();

  beforeEach(() => {
    mockOnParamsChange.mockClear();
  });

  test('renders all parameter inputs', () => {
    render(
      <ParameterPanel params={defaultParams} onParamsChange={mockOnParamsChange} />
    );

    expect(screen.getByDisplayValue('52')).toBeInTheDocument(); // Tile Size
    expect(screen.getByDisplayValue('6')).toBeInTheDocument(); // Width
    expect(screen.getByDisplayValue('1')).toBeInTheDocument(); // Sample
    expect(screen.getAllByDisplayValue('0')).toHaveLength(2); // Outline and Shadow Scale
    expect(screen.getByDisplayValue('1024')).toBeInTheDocument(); // Preview Max Width
  });

  test('calls onParamsChange when tile size is updated', () => {
    render(
      <ParameterPanel params={defaultParams} onParamsChange={mockOnParamsChange} />
    );

    const tileSizeInput = screen.getByDisplayValue('52');
    fireEvent.change(tileSizeInput, { target: { value: '64' } });

    expect(mockOnParamsChange).toHaveBeenCalledWith({
      ...defaultParams,
      tileSize: 64
    });
  });

  test('calls onParamsChange when width is updated', () => {
    render(
      <ParameterPanel params={defaultParams} onParamsChange={mockOnParamsChange} />
    );

    const widthInput = screen.getByDisplayValue('6');
    fireEvent.change(widthInput, { target: { value: '8' } });

    expect(mockOnParamsChange).toHaveBeenCalledWith({
      ...defaultParams,
      width: 8
    });
  });

  test('calls onParamsChange when useShadowImages checkbox is toggled', () => {
    render(
      <ParameterPanel params={defaultParams} onParamsChange={mockOnParamsChange} />
    );

    const checkboxes = screen.getAllByRole('checkbox');
    const shadowCheckbox = checkboxes.find(cb => 
      cb.nextSibling && cb.nextSibling.textContent === 'Use Shadow Images'
    );
    fireEvent.click(shadowCheckbox);

    expect(mockOnParamsChange).toHaveBeenCalledWith({
      ...defaultParams,
      useShadowImages: true
    });
  });

  test('shadow scale input is disabled when useShadowImages is true', () => {
    const paramsWithShadowImages = {
      ...defaultParams,
      useShadowImages: true
    };

    render(
      <ParameterPanel params={paramsWithShadowImages} onParamsChange={mockOnParamsChange} />
    );

    const shadowScaleInputs = screen.getAllByDisplayValue('0');
    const shadowScaleInput = shadowScaleInputs.find(input => 
      input.getAttribute('step') === '0.1'
    );
    
    expect(shadowScaleInput).toBeDisabled();
  });

  test('missing shadow policy select is disabled when useShadowImages is false', () => {
    render(
      <ParameterPanel params={defaultParams} onParamsChange={mockOnParamsChange} />
    );

    const select = screen.getByRole('combobox');
    expect(select).toBeDisabled();
  });

  test('calls onParamsChange when remove color is updated', () => {
    render(
      <ParameterPanel params={defaultParams} onParamsChange={mockOnParamsChange} />
    );

    const removeColorInput = screen.getByPlaceholderText('ff0000');
    fireEvent.change(removeColorInput, { target: { value: '00ff00' } });

    expect(mockOnParamsChange).toHaveBeenCalledWith({
      ...defaultParams,
      removeColor: '00ff00'
    });
  });
});