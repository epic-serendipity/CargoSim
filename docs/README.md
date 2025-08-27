# CargoSim Documentation

Welcome to the comprehensive documentation for CargoSim, the professional hub-and-spoke logistics simulator.

## Documentation Structure

### 📚 [User Guides](USER_GUIDES/)
Essential information for getting started and using CargoSim:
- Getting started guide
- Configuration walkthrough
- Troubleshooting common issues
- User interface reference

### 🚀 [Features](FEATURES/)
Detailed documentation of CargoSim's capabilities:
- Custom aircraft system
- Fleet builder functionality
- Smart targeting algorithms
- Visual themes and customization
- Temporary fleet system

### 🛠️ [Development](DEVELOPMENT/)
Information for developers and contributors:
- Architecture overview
- Contributing guidelines
- Code standards and practices
- Testing and quality assurance
- Agent system documentation

### 📖 [API Reference](API/)
Technical reference for developers:
- Class and method documentation
- Configuration schemas
- Extension points
- Integration examples

## Quick Start

### Installation
```bash
# Development installation
pip install -e .

# With video support
pip install -e .[video]
```

### Running CargoSim
```bash
# GUI Control Panel
python -m cargosim

# Headless mode
python -m cargosim --headless --periods 10 --seed 42

# Custom aircraft demo
python examples/advanced/custom_aircraft.py
```

## Core Concepts

### Simulation Model
- **Periods**: Alternate AM/PM cycles
- **Resources**: A, B, C, D resource types
- **Operations**: Consume C and D resources
- **Aircraft**: Ferry supplies between hub and spokes

### Key Features
- **Visual Themes**: 5 built-in themes with customization
- **Custom Aircraft**: Unique visual representations
- **Recording System**: MP4 and PNG output
- **Fleet Builder**: Visual fleet composition tool
- **Smart Targeting**: Advanced resource management

## Documentation by User Type

### 🎯 **New Users**
Start here to learn the basics:
1. [Getting Started Guide](USER_GUIDES/getting_started.md)
2. [Basic Configuration](USER_GUIDES/configuration.md)
3. [First Simulation](USER_GUIDES/first_simulation.md)

### 🔧 **Power Users**
Explore advanced features:
1. [Custom Aircraft](FEATURES/custom_aircraft.md)
2. [Fleet Builder](FEATURES/fleet_builder.md)
3. [Smart Targeting](FEATURES/smart_targeting.md)
4. [Visual Customization](FEATURES/visual_themes.md)

### 👨‍💻 **Developers**
Contribute to the project:
1. [Architecture Overview](DEVELOPMENT/architecture.md)
2. [Contributing Guidelines](DEVELOPMENT/contributing.md)
3. [Testing Guide](DEVELOPMENT/testing.md)
4. [API Reference](API/index.md)

### 🎨 **Designers**
Customize the visual experience:
1. [Theme System](FEATURES/visual_themes.md)
2. [Custom Aircraft](FEATURES/custom_aircraft.md)
3. [UI Customization](FEATURES/ui_customization.md)

## Feature Highlights

### 🎮 **Interactive Simulation**
- Real-time visualization with Pygame
- Pause, step, and speed controls
- Fullscreen and windowed modes
- Keyboard shortcuts for quick access

### 🎨 **Visual Excellence**
- Multiple built-in themes
- Customizable color schemes
- Smooth animations and transitions
- Responsive design for all screen sizes

### 📊 **Advanced Analytics**
- Resource consumption tracking
- Performance metrics
- Statistical analysis
- Export capabilities

### 🔧 **Extensibility**
- Plugin architecture
- Custom aircraft support
- Configuration system
- API for external tools

## Getting Help

### 📖 **Documentation**
- Check this index for relevant sections
- Use the search functionality
- Review examples and tutorials

### 🐛 **Troubleshooting**
- [Common Issues](USER_GUIDES/troubleshooting.md)
- [Error Messages](USER_GUIDES/error_reference.md)
- [Performance Tips](USER_GUIDES/performance.md)

### 💬 **Community**
- GitHub Issues for bug reports
- Discussions for questions
- Wiki for community knowledge
- Contributing for improvements

## Project Information

### 📋 **Requirements**
- Python 3.10+
- Pygame 2.5+
- Tkinter (built-in on most systems)

### 🏗️ **Architecture**
- Modular design for maintainability
- Separation of concerns
- Clean interfaces between components
- Comprehensive testing

### 📈 **Development Status**
- **Current Version**: Beta
- **Stability**: Production ready
- **Active Development**: Yes
- **Contributions**: Welcome

## Contributing to Documentation

### 📝 **Writing Guidelines**
1. Use clear, concise language
2. Include practical examples
3. Add screenshots for visual features
4. Keep information up to date
5. Follow the established structure

### 🔄 **Update Process**
1. Make changes in your branch
2. Test all examples and links
3. Submit a pull request
4. Include a summary of changes
5. Request review from maintainers

### 📚 **Documentation Standards**
- Markdown format
- Consistent heading structure
- Code examples with syntax highlighting
- Cross-references between sections
- Regular review and updates

## Version History

### 📅 **Recent Updates**
- **v2.0**: Complete reorganization and documentation overhaul
- **v1.5**: Enhanced custom aircraft system
- **v1.0**: Initial release with core functionality

### 🔮 **Future Plans**
- Interactive tutorials
- Video documentation
- API documentation generator
- Community-contributed examples
- Multi-language support

---

*This documentation is maintained by the CargoSim development team and community contributors. For questions or suggestions, please open an issue or discussion on GitHub.*
