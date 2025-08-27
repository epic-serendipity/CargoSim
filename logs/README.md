# CargoSim Log Files

This directory contains log files generated during CargoSim execution.

## Directory Structure

### `runtime/`
Runtime execution logs:
- Simulation progress
- Performance metrics
- User interactions
- System events

### `debug/`
Debug and development logs:
- Detailed execution traces
- Error diagnostics
- Performance profiling
- Development information

## Log File Types

### 1. Runtime Logs (`cargo_sim_runtime.log`)
**Purpose**: Track simulation execution and user interactions
**Content**:
- Simulation start/stop events
- Period transitions
- Resource consumption
- Aircraft movements
- User control inputs

**Usage**: Monitor simulation progress and troubleshoot runtime issues

### 2. Debug Logs (`cargo_sim_debug.log`)
**Purpose**: Detailed debugging information for developers
**Content**:
- Function entry/exit points
- Variable values and state changes
- Performance measurements
- Error stack traces
- Memory usage statistics

**Usage**: Debug issues and optimize performance

## Log Configuration

### Log Levels
- **INFO**: General information and progress
- **DEBUG**: Detailed debugging information
- **WARNING**: Potential issues (non-fatal)
- **ERROR**: Errors that affect functionality
- **CRITICAL**: Fatal errors that stop execution

### Log Format
```
[2024-01-15 14:30:25] [INFO] [simulation] Simulation started with 60 periods
[2024-01-15 14:30:26] [DEBUG] [renderer] Frame rendered in 16.67ms
[2024-01-15 14:30:27] [WARNING] [simulation] Low resource levels detected
```

## Log Management

### Automatic Rotation
- Logs are automatically rotated when they reach size limits
- Old logs are compressed and archived
- Configurable retention policies

### Manual Management
```bash
# View recent runtime logs
tail -f logs/runtime/cargo_sim_runtime.log

# Search for errors
grep "ERROR" logs/debug/cargo_sim_debug.log

# Archive old logs
tar -czf logs_archive_$(date +%Y%m%d).tar.gz logs/
```

## Log Analysis

### Common Patterns
1. **Performance Issues**: Look for slow frame times
2. **Resource Problems**: Check for resource depletion warnings
3. **User Errors**: Identify common user mistakes
4. **System Issues**: Monitor for system resource problems

### Tools
- **Text editors**: VS Code, Notepad++, Vim
- **Log viewers**: LogViewer, LogExpert
- **Command line**: grep, awk, sed
- **Python**: Built-in logging analysis

## Troubleshooting

### Missing Logs
- Check file permissions
- Verify log directory exists
- Ensure logging is enabled
- Check disk space

### Large Log Files
- Enable log rotation
- Reduce log verbosity
- Archive old logs
- Clean up temporary files

### Performance Impact
- Use appropriate log levels
- Avoid excessive logging in loops
- Use async logging when possible
- Monitor log file sizes

## Best Practices

1. **Log Level Selection**: Use appropriate levels for production vs development
2. **Sensitive Information**: Never log passwords, API keys, or personal data
3. **Performance**: Balance detail with performance impact
4. **Retention**: Implement log rotation and cleanup policies
5. **Monitoring**: Set up alerts for critical errors

## Configuration

### Log Settings
```python
from cargosim.core import setup_logging

# Configure logging
setup_logging(
    level="INFO",
    log_file="logs/runtime/cargo_sim_runtime.log",
    debug_file="logs/debug/cargo_sim_debug.log",
    max_size=10*1024*1024,  # 10MB
    backup_count=5
)
```

### Environment Variables
- `CARGOSIM_LOG_LEVEL`: Set default log level
- `CARGOSIM_LOG_DIR`: Specify log directory
- `CARGOSIM_DEBUG`: Enable debug logging

## Contributing

When adding new logging:
1. Use appropriate log levels
2. Include relevant context
3. Follow established format
4. Consider performance impact
5. Update this documentation
