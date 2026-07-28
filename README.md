# OZX Image Atlas Tool

A web-based tool for creating image atlases using Python PIL backend and React frontend. This tool allows you to combine multiple sprite images into a single atlas with various customization options.

## Features

- **Import multiple sprite images** - Drag & drop interface with reordering
- **Parameter customization** - Tile size, width, outline, color removal, etc.
- **Shadow support** - Two modes: scale-based shadows or separate shadow images
- **Background image support** - Optional background tiling
- **Real-time preview** - See changes instantly
- **Export to PNG** - Download the final atlas, as separate sprite and shadow sheets (default) or one merged sheet

## Quick Start

### Option 1: Automated Setup
```bash
./start.sh
```

This will install dependencies and start both backend and frontend automatically.

### Option 2: Manual Setup

#### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm start
```

### Testing Setup
```bash
python3 test_setup.py
```

## Usage

1. **Import Sprites**: Drag and drop your sprite images into the "Sprites" section
2. **Configure Parameters**: Adjust tile size, width, effects in the "Parameters" section
3. **Add Shadows** (optional): 
   - Enable "Use Shadow Images" and import matching shadow files, OR
   - Set "Shadow Scale" > 0 for automatic shadows
4. **Add Background** (optional): Enable "Use Background" and import a background image
5. **Preview**: The atlas updates in real-time as you make changes
6. **Export**: Pick the layer mode, then click "Export Atlas"
   - *Separate sprite & shadow sheets* (default): downloads `atlas.png` (sprites only) and `atlas_shadow.png` (shadows **and** backgrounds), aligned cell for cell
   - *Single merged sheet*: downloads one `atlas.png` with everything composited
   - The preview always shows the merged result, whichever mode is selected

## Shadow Image Matching

When using shadow images, the tool automatically matches sprites with shadows based on filename:

- **Exact match**: `sprite.png` → `sprite.png` (shadow)
- **Suffix removal**: `sprite.png` → `sprite_shadow.png`, `sprite-shadow.png`, etc.
- **Normalization**: Case-insensitive, handles spaces and special characters

## Parameters

- **Tile Size**: Base size for each tile (default: 52px)
- **Width**: Number of tile columns (default: 6)
- **Sample**: Take every Nth image (default: 1 = all images)
- **Outline**: Add soft outline width (0 = disabled)
- **Remove Color**: Remove specific color (hex format, e.g., "ff0000")
- **Shadow Scale**: Scale factor for automatic shadows (0 = disabled)
- **Use Shadow Images**: Enable separate shadow image matching
- **Missing Shadow Policy**: How to handle missing shadows
- **Use Background**: Enable background image tiling

## API Endpoints

- `POST /v1/atlas/preview` - Generate preview atlas
- `POST /v1/atlas/export` - Export final atlas (ZIP of both sheets, or a single PNG with `exportLayerMode: "combined"`)
- `GET /` - Health check

## Requirements

- Python 3.7+
- Node.js 14+
- PIL/Pillow
- FastAPI
- React

## Architecture

```
frontend/          # React application
├── src/
│   ├── App.js           # Main application
│   ├── components/      # UI components
│   └── index.css        # Styles

backend/           # Python FastAPI server
├── main.py              # API endpoints
├── atlas_core.py        # Core image processing
├── atlas_service.py     # Business logic
├── shadow_matching.py   # Shadow file matching
└── requirements.txt     # Python dependencies
```

Open http://localhost:3000 in your browser.

## 🧪 Testing

### Quick Test

```bash
python3 test_setup.py          # Verify setup
./run_tests.sh --backend-only   # Backend tests
./run_tests.sh --frontend-only  # Frontend tests
```

### Full Test Suite

```bash
./run_tests.sh --all           # All tests (requires running servers)
```

## 📦 Project Status

✅ **Core Features Implemented**
- ✅ Backend: FastAPI with PIL image processing
- ✅ Frontend: React with drag & drop interface
- ✅ Real-time atlas preview
- ✅ PNG export functionality
- ✅ Shadow image matching (useShadowImages)
- ✅ Background image support
- ✅ Parameter customization
- ✅ Input validation & error handling

✅ **Code Quality**
- ✅ Unit tests for backend (42 tests, 90%+ coverage)
- ✅ Unit tests for frontend (18 tests)
- ✅ Integration test framework
- ✅ E2E test infrastructure
- ✅ Type safety and validation

✅ **Production Ready**
- ✅ Docker deployment support
- ✅ Security hardening
- ✅ Performance optimization
- ✅ Comprehensive documentation
- ✅ Error handling & monitoring

## 🔧 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment instructions.

## 📄 Files Structure

```
ozx_image_atlas/
├── README.md                 # This file
├── DEPLOYMENT.md            # Production deployment guide
├── start.sh                # Development startup script
├── run_tests.sh            # Test runner script
├── test_setup.py           # Setup verification script
├── backend/                # Python FastAPI backend
│   ├── main.py             # API endpoints
│   ├── atlas_core.py       # Core image processing
│   ├── atlas_service.py    # Business logic
│   ├── shadow_matching.py  # Shadow file matching
│   ├── requirements.txt    # Python dependencies
│   └── tests/              # Backend unit tests
├── frontend/               # React frontend
│   ├── src/
│   │   ├── App.js          # Main application
│   │   ├── components/     # UI components
│   │   └── __tests__/      # Frontend tests
│   ├── package.json        # Node.js dependencies
│   └── build/              # Production build
└── tests/                  # Integration & E2E tests
    ├── integration/        # API integration tests
    └── e2e/               # Browser automation tests
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `./run_tests.sh --all`
4. Submit a pull request

## 📝 License

This project is developed for educational and internal use.