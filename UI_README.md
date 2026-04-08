# 🎨 Interactive Web Dashboard

## Quick Start

Launch the interactive web dashboard:

```bash
python launch_ui.py
```

The dashboard will open automatically in your browser at `http://localhost:8501`

## Features

### 1. 📝 Quick Start Mode
- Enter API requirements in natural language
- View example prompts
- One-click pipeline execution
- Real-time progress tracking

### 2. 🎨 Visual BRD Editor
- Interactive drag-and-drop interface
- Pre-built templates for common requirements
- Section-by-section editing:
  - Basic project information
  - Business goals
  - Functional requirements
  - Non-functional requirements
  - Stakeholders
  - Acceptance criteria
- Export to JSON
- Save and load BRDs

### 3. ⚡ Real-Time Progress Tracking
- Live pipeline execution status
- Step-by-step progress visualization
- Detailed logs viewer
- Time tracking
- Error reporting

### 4. 📊 Code Diff Viewer
- Multiple diff modes:
  - Side-by-side comparison
  - Unified diff (git-style)
  - Line-by-line detailed diff
- Syntax highlighting
- Change statistics
- Upload or paste code for comparison

### 5. 📂 Results Dashboard
- View generated BRD
- Browse Jira stories
- Explore generated code files
- Download individual files or complete package
- Real-time metrics

## Usage

### Quick Start

1. Launch the dashboard: `python launch_ui.py`
2. Select "Quick Start" mode
3. Enter your API requirements (e.g., "Create a blog API with CRUD operations")
4. Click "▶️ Run Pipeline"
5. Watch real-time progress
6. Download generated files

### Visual BRD Builder

1. Select "Visual BRD Editor" mode
2. Fill in each section using the tabs:
   - Add project title and description
   - Add business goals
   - Define functional requirements
   - Select non-functional requirements from templates
   - Add stakeholders
   - Define acceptance criteria
3. Click "▶️ Generate Code from BRD"
4. Monitor pipeline execution
5. Review and download results

### Upload Existing BRD

1. Select "Upload BRD JSON" mode
2. Upload your BRD JSON file
3. Review the loaded data
4. Click "Process Uploaded BRD"

## Configuration

Access advanced settings in the sidebar:
- **LLM Temperature**: Control randomness in code generation (0.0-1.0)
- **Max Retries**: Number of retry attempts for failed operations
- **Auto-fix**: Automatically fix test failures

## Keyboard Shortcuts

- `Ctrl + R`: Reload the page
- `Ctrl + C`: Stop the server (in terminal)

## Tips

- Use example prompts as templates
- Be specific in your requirements for better code generation
- Save your BRDs for reuse
- Compare generated code with previous versions using the diff viewer
- Check the logs for detailed execution information

## Troubleshooting

### Dashboard won't start
- Ensure Streamlit is installed: `pip install streamlit`
- Check if port 8501 is available
- Try: `streamlit run src/ui/app.py`

### Pipeline doesn't run
- Verify Azure OpenAI credentials in `.env`
- Check logs in the dashboard
- Ensure all dependencies are installed

### Files not generated
- Check the logs tab for errors
- Verify output directory permissions
- Ensure sufficient disk space

## Architecture

```
src/ui/
├── app.py                      # Main Streamlit application
├── components/
│   ├── __init__.py
│   ├── brd_editor.py          # Visual BRD editor
│   ├── code_diff.py           # Code diff viewer
│   └── progress_tracker.py    # Real-time progress tracking
└── ...
```

## API Reference

The dashboard integrates with the existing pipeline:
- Uses `react_pipeline()` from `orchestrator.py`
- Reads from `output/` directory
- Saves BRDs to `saved_brds/`

## Customization

You can customize the dashboard by modifying:
- `app.py`: Main layout and flow
- `components/brd_editor.py`: BRD editor templates
- `components/code_diff.py`: Diff visualization
- `components/progress_tracker.py`: Progress display

## Future Enhancements

- [ ] Real-time collaboration
- [ ] Version history
- [ ] Git integration
- [ ] Deployment automation
- [ ] Custom templates
- [ ] API testing interface
