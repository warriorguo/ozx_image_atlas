import {
  STORAGE_KEY,
  DEFAULT_PARAMS,
  loadStoredParams,
  saveParams,
  clearStoredParams,
} from '../utils/paramStorage';

const store = (value) => window.localStorage.setItem(STORAGE_KEY, value);
const stored = () => JSON.parse(window.localStorage.getItem(STORAGE_KEY));

describe('paramStorage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  describe('loadStoredParams', () => {
    test('returns defaults when nothing was saved', () => {
      expect(loadStoredParams()).toEqual(DEFAULT_PARAMS);
    });

    test('returns a fresh object rather than the shared defaults', () => {
      const loaded = loadStoredParams();
      loaded.tileSize = 64;
      expect(DEFAULT_PARAMS.tileSize).toBe(192);
    });

    test('restores saved values', () => {
      store(JSON.stringify({
        tileSize: 64,
        width: 8,
        shadowScale: 1.5,
        useShadowImages: true,
        missingShadowPolicy: 'fail',
        exportLayerMode: 'combined',
      }));

      expect(loadStoredParams()).toEqual({
        ...DEFAULT_PARAMS,
        tileSize: 64,
        width: 8,
        shadowScale: 1.5,
        useShadowImages: true,
        missingShadowPolicy: 'fail',
        exportLayerMode: 'combined',
      });
    });

    test('drops out-of-range values but keeps the valid ones alongside', () => {
      store(JSON.stringify({ tileSize: 9999, width: 8 }));

      const loaded = loadStoredParams();
      expect(loaded.tileSize).toBe(DEFAULT_PARAMS.tileSize);
      expect(loaded.width).toBe(8);
    });

    test.each([
      ['tileSize', 0],
      ['tileSize', 513],
      ['tileSize', 64.5],
      ['tileSize', '64'],
      ['width', 21],
      ['sample', 0],
      ['outline', 51],
      ['removeColorThreshold', 256],
      ['shadowScale', 5.1],
      ['shadowScale', -1],
      ['useShadowImages', 'yes'],
      ['skipDuplicate', 1],
      ['missingShadowPolicy', 'nope'],
      ['exportLayerMode', 'zip'],
      ['previewMaxWidth', 100],
      ['previewMaxWidth', 8192],
      ['removeColor', 'nothex'],
      ['removeColor', 42],
    ])('rejects invalid %s (%p)', (key, value) => {
      store(JSON.stringify({ [key]: value }));
      expect(loadStoredParams()[key]).toEqual(DEFAULT_PARAMS[key]);
    });

    test('accepts a hex remove color, with or without a leading hash', () => {
      store(JSON.stringify({ removeColor: 'ff0000' }));
      expect(loadStoredParams().removeColor).toBe('ff0000');

      store(JSON.stringify({ removeColor: '#00FF00' }));
      expect(loadStoredParams().removeColor).toBe('#00FF00');
    });

    test('accepts the longer hex forms the backend also parses', () => {
      store(JSON.stringify({ removeColor: 'ff0000ff' }));
      expect(loadStoredParams().removeColor).toBe('ff0000ff');
    });

    test('rejects a hex color too short for the backend to parse', () => {
      store(JSON.stringify({ removeColor: 'ff0' }));
      expect(loadStoredParams().removeColor).toBeNull();
    });

    test('accepts an explicit null remove color', () => {
      store(JSON.stringify({ removeColor: null }));
      expect(loadStoredParams().removeColor).toBeNull();
    });

    test('never restores tile background assignments', () => {
      store(JSON.stringify({ tileBackgroundAssignments: { 'gone.png': 'bg.png' } }));
      expect(loadStoredParams().tileBackgroundAssignments).toEqual({});
    });

    test('ignores unknown keys', () => {
      store(JSON.stringify({ retiredParam: 'x', tileSize: 64 }));

      const loaded = loadStoredParams();
      expect(loaded.retiredParam).toBeUndefined();
      expect(loaded.tileSize).toBe(64);
    });

    test.each([
      ['malformed JSON', 'not json at all'],
      ['a JSON array', '[1, 2, 3]'],
      ['a JSON scalar', '"just a string"'],
      ['null', 'null'],
    ])('falls back to defaults on %s', (_label, raw) => {
      store(raw);
      expect(loadStoredParams()).toEqual(DEFAULT_PARAMS);
    });

    test('falls back to defaults when storage throws', () => {
      const spy = jest.spyOn(window.localStorage.__proto__, 'getItem')
        .mockImplementation(() => { throw new Error('denied'); });

      expect(loadStoredParams()).toEqual(DEFAULT_PARAMS);
      spy.mockRestore();
    });
  });

  describe('saveParams', () => {
    test('persists the parameters', () => {
      saveParams({ ...DEFAULT_PARAMS, tileSize: 64, exportLayerMode: 'combined' });

      expect(stored().tileSize).toBe(64);
      expect(stored().exportLayerMode).toBe('combined');
    });

    test('omits tile background assignments', () => {
      saveParams({ ...DEFAULT_PARAMS, tileBackgroundAssignments: { 'a.png': 'bg.png' } });

      expect(stored()).not.toHaveProperty('tileBackgroundAssignments');
    });

    test('round-trips through loadStoredParams', () => {
      const params = {
        ...DEFAULT_PARAMS,
        tileSize: 128,
        width: 4,
        outline: 2,
        removeColor: 'ff00ff',
        removeColorThreshold: 12,
        shadowScale: 0.5,
        useShadowImages: true,
        missingShadowPolicy: 'ignoreSprite',
        useBackground: true,
        skipDuplicate: false,
        previewMaxWidth: 2048,
        exportLayerMode: 'combined',
        tileBackgroundAssignments: { 'a.png': 'bg.png' },
      };

      saveParams(params);

      expect(loadStoredParams()).toEqual({ ...params, tileBackgroundAssignments: {} });
    });

    test('swallows storage failures', () => {
      const spy = jest.spyOn(window.localStorage.__proto__, 'setItem')
        .mockImplementation(() => { throw new Error('quota exceeded'); });

      expect(() => saveParams(DEFAULT_PARAMS)).not.toThrow();
      spy.mockRestore();
    });
  });

  describe('clearStoredParams', () => {
    test('removes the saved parameters', () => {
      saveParams({ ...DEFAULT_PARAMS, tileSize: 64 });
      clearStoredParams();

      expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
      expect(loadStoredParams()).toEqual(DEFAULT_PARAMS);
    });
  });
});
