"""
Help system for CargoSim with comprehensive documentation and search capabilities.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
from typing import Optional

from ..core.utils import log_runtime_event, log_exception
from ..rendering.themes.default_fonts import DEFAULT_FONT_BOLD


class HelpSystem:
    """Comprehensive help system for CargoSim advanced features."""
    
    def __init__(self, parent):
        self.parent = parent
        self.help_window = None
        self.current_topic = None
        self.help_data = self._load_help_data()
        
    def _load_help_data(self) -> dict:
        """Load help content and documentation."""
        return {
            'getting_started': {
                'title': 'Getting Started with Advanced Features',
                'content': self._get_getting_started_content(),
                'sections': ['Overview', 'First Steps', 'Basic Configuration']
            },
            'performance_monitoring': {
                'title': 'Performance Monitoring Guide',
                'content': self._get_performance_monitoring_content(),
                'sections': ['System Metrics', 'Performance Trends', 'Alerts', 'Troubleshooting']
            },
            'analytics': {
                'title': 'Analytics and Predictive Modeling',
                'content': self._get_analytics_content(),
                'sections': ['Demand Forecasting', 'Cost Prediction', 'Performance Prediction', 'Model Accuracy']
            },
            'export_integration': {
                'title': 'Data Export and Integration',
                'content': self._get_export_integration_content(),
                'sections': ['Export Formats', 'Cloud Storage', 'Database Integration', 'API Endpoints']
            },
            'troubleshooting': {
                'title': 'Troubleshooting Guide',
                'content': self._get_troubleshooting_content(),
                'sections': ['Common Issues', 'Error Messages', 'Performance Problems', 'Integration Issues']
            },
            'advanced_configuration': {
                'title': 'Advanced Configuration',
                'content': self._get_advanced_configuration_content(),
                'sections': ['Performance Tuning', 'Custom Integrations', 'Security Settings', 'Backup & Recovery']
            }
        }
    
    def show_help(self, topic: str = 'getting_started'):
        """Show the help window with the specified topic."""
        if self.help_window and self.help_window.winfo_exists():
            self.help_window.lift()
            self.help_window.focus_force()
        else:
            self._create_help_window()
        
        self._show_topic(topic)
    
    def _create_help_window(self):
        """Create the main help window."""
        self.help_window = tk.Toplevel(self.parent)
        self.help_window.title("CargoSim Advanced Features Help")
        self.help_window.geometry("900x700")
        self.help_window.minsize(800, 600)
        
        # Configure window
        self.help_window.transient(self.parent)
        self.help_window.grab_set()
        
        # Create main layout
        self._create_help_layout()
        
        # Center window
        self.help_window.update_idletasks()
        x = (self.help_window.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.help_window.winfo_screenheight() // 2) - (700 // 2)
        self.help_window.geometry(f"900x700+{x}+{y}")
        
        # Bind close event
        self.help_window.protocol("WM_DELETE_WINDOW", self._close_help)
        
        log_runtime_event("Help system window created")
    
    def _create_help_layout(self):
        """Create the help window layout."""
        # Main frame
        main_frame = ttk.Frame(self.help_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Top toolbar
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill="x", pady=(0, 10))
        
        # Search box
        ttk.Label(toolbar_frame, text="Search:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search_change)
        search_entry = ttk.Entry(toolbar_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side="left", padx=(0, 10))
        
        # Help buttons
        ttk.Button(toolbar_frame, text="Print", command=self._print_help).pack(side="left", padx=5)
        ttk.Button(toolbar_frame, text="Export", command=self._export_help).pack(side="left", padx=5)
        ttk.Button(toolbar_frame, text="Online Docs", command=self._open_online_docs).pack(side="left", padx=5)
        
        # Main content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)
        
        # Left sidebar - Navigation
        nav_frame = ttk.LabelFrame(content_frame, text="Navigation", padding=10)
        nav_frame.pack(side="left", fill="y", padx=(0, 10))
        
        # Topic listbox
        self.topic_listbox = tk.Listbox(nav_frame, width=25, height=20)
        self.topic_listbox.pack(fill="both", expand=True)
        self.topic_listbox.bind('<<ListboxSelect>>', self._on_topic_select)
        
        # Populate topics
        for _topic_key, topic_data in self.help_data.items():
            self.topic_listbox.insert(tk.END, topic_data['title'])
        
        # Right content area
        content_area_frame = ttk.Frame(content_frame)
        content_area_frame.pack(side="right", fill="both", expand=True)
        
        # Content title
        self.content_title_label = ttk.Label(content_area_frame, text="", font=DEFAULT_FONT_BOLD)
        self.content_title_label.pack(anchor="w", pady=(0, 10))
        
        # Content text area
        text_frame = ttk.Frame(content_area_frame)
        text_frame.pack(fill="both", expand=True)
        
        # Create text widget with scrollbar
        self.content_text = tk.Text(text_frame, wrap="word", padx=10, pady=10)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=scrollbar.set)
        
        self.content_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bottom status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Ready", style="Muted.TLabel")
        self.status_label.pack(side="left")
        
        # Section navigation
        self.section_var = tk.StringVar()
        section_combo = ttk.Combobox(status_frame, textvariable=self.section_var, 
                                    state="readonly", width=30)
        section_combo.pack(side="right")
        section_combo.bind('<<ComboboxSelected>>', self._on_section_select)
        
        # Set initial topic
        self._show_topic('getting_started')
    
    def _show_topic(self, topic: str):
        """Show content for the specified topic."""
        if topic not in self.help_data:
            return
        
        self.current_topic = topic
        topic_data = self.help_data[topic]
        
        # Update title
        self.content_title_label.configure(text=topic_data['title'])
        
        # Update content
        self.content_text.delete(1.0, tk.END)
        self.content_text.insert(1.0, topic_data['content'])
        
        # Update section navigation
        section_combo = self.help_window.nametowidget(self.status_label.master.children['!combobox'])
        section_combo['values'] = topic_data['sections']
        if topic_data['sections']:
            section_combo.set(topic_data['sections'][0])
        
        # Update status
        self.status_label.configure(text=f"Showing: {topic_data['title']}")
        
        # Select topic in navigation
        for i, topic_key in enumerate(self.help_data.keys()):
            if topic_key == topic:
                self.topic_listbox.selection_clear(0, tk.END)
                self.topic_listbox.selection_set(i)
                self.topic_listbox.see(i)
                break
    
    def _on_topic_select(self, event):
        """Handle topic selection in navigation."""
        selection = self.topic_listbox.curselection()
        if selection:
            topic_index = selection[0]
            topic_key = list(self.help_data.keys())[topic_index]
            self._show_topic(topic_key)
    
    def _on_section_select(self, event):
        """Handle section selection."""
        # Implementation for section navigation
        pass
    
    def _on_search_change(self, *args):
        """Handle search input changes."""
        search_term = self.search_var.get().lower()
        if len(search_term) < 2:
            return
        
        # Search through help content
        results = []
        for topic_key, topic_data in self.help_data.items():
            if (search_term in topic_data['title'].lower() or 
                search_term in topic_data['content'].lower()):
                results.append(topic_key)
        
        if results:
            # Show first result
            self._show_topic(results[0])
            self.status_label.configure(text=f"Search result: {self.help_data[results[0]]['title']}")
        else:
            self.status_label.configure(text="No search results found")
    
    def _print_help(self):
        """Print the current help content."""
        try:
            if self.current_topic:
                topic_data = self.help_data[self.current_topic]
                print(f"\n{'='*60}")
                print(f"CargoSim Help: {topic_data['title']}")
                print(f"{'='*60}\n")
                print(topic_data['content'])
                print(f"\n{'='*60}")
                self.status_label.configure(text="Content printed to console")
        except Exception as e:
            log_exception(e, "Help printing failed")
            messagebox.showerror("Print Error", f"Failed to print help: {str(e)}")
    
    def _export_help(self):
        """Export help content to file."""
        try:
            if not self.current_topic:
                return
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("HTML files", "*.html"),
                    ("Markdown files", "*.md"),
                    ("All files", "*.*")
                ],
                title="Export Help Content"
            )
            
            if filename:
                topic_data = self.help_data[self.current_topic]
                
                if filename.endswith('.html'):
                    content = self._format_as_html(topic_data)
                elif filename.endswith('.md'):
                    content = self._format_as_markdown(topic_data)
                else:
                    content = self._format_as_text(topic_data)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.status_label.configure(text=f"Help exported to {filename}")
                messagebox.showinfo("Export Successful", f"Help content exported to {filename}")
                
        except Exception as e:
            log_exception(e, "Help export failed")
            messagebox.showerror("Export Error", f"Failed to export help: {str(e)}")
    
    def _open_online_docs(self):
        """Open online documentation in web browser."""
        try:
            # This would open the actual online documentation URL
            webbrowser.open("https://cargosim-docs.example.com")
            self.status_label.configure(text="Opening online documentation...")
        except Exception as e:
            log_exception(e, "Failed to open online docs")
            messagebox.showerror("Error", "Failed to open online documentation")
    
    def _close_help(self):
        """Close the help window."""
        if self.help_window:
            self.help_window.destroy()
            self.help_window = None
    
    def _format_as_html(self, topic_data: dict) -> str:
        """Format help content as HTML."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>CargoSim Help - {topic_data['title']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
        .content {{ line-height: 1.6; }}
    </style>
</head>
<body>
    <h1>{topic_data['title']}</h1>
    <div class="content">
        {topic_data['content'].replace(chr(10), '<br>')}
    </div>
</body>
</html>"""
    
    def _format_as_markdown(self, topic_data: dict) -> str:
        """Format help content as Markdown."""
        return f"# {topic_data['title']}\n\n{topic_data['content']}"
    
    def _format_as_text(self, topic_data: dict) -> str:
        """Format help content as plain text."""
        return f"{topic_data['title']}\n{'='*len(topic_data['title'])}\n\n{topic_data['content']}"
    
    # Help content methods
    def _get_getting_started_content(self) -> str:
        return """Welcome to CargoSim Advanced Features!

This guide will help you get started with the powerful new capabilities that have been added to CargoSim.

OVERVIEW
CargoSim Advanced Features provides:
• Real-time performance monitoring
• Predictive analytics and forecasting
• Advanced data export and integration
• Enhanced visualizations and user experience
• Professional reporting and documentation

FIRST STEPS
1. Open the Advanced Features tab in the main GUI
2. Enable the features you want to use
3. Configure performance monitoring settings
4. Set up your preferred export formats
5. Test the analytics and prediction tools

BASIC CONFIGURATION
• Performance Display: Shows real-time system metrics
• Cost Display: Tracks operational costs and trends
• Speed Indicators: Visual feedback for aircraft movement
• Motion Blur: Enhanced visual effects for realism
• Cargo Animations: Loading/unloading progress indicators

The system is designed to be intuitive and user-friendly. Most features can be enabled/disabled independently, allowing you to customize your experience based on your needs and system capabilities."""
    
    def _get_performance_monitoring_content(self) -> str:
        return """Performance Monitoring Guide

CargoSim now includes comprehensive performance monitoring to help you optimize your simulation and system performance.

SYSTEM METRICS
The performance monitor tracks:
• CPU Usage: Current and historical CPU utilization
• Memory Usage: RAM consumption in real-time
• Uptime: System running time and stability
• Performance Trends: Patterns and changes over time
• Alert System: Notifications for performance issues

PERFORMANCE TRENDS
• Increasing: Performance is degrading (orange indicator)
• Decreasing: Performance is improving (green indicator)
• Stable: Performance is consistent (blue indicator)

Trends are calculated using linear regression analysis of historical data, providing insights into system behavior patterns.

ALERTS
The system automatically generates alerts when:
• CPU usage exceeds 80%
• Memory usage exceeds 90%
• Performance degradation is detected
• System resources are constrained

TROUBLESHOOTING
Common performance issues and solutions:

High CPU Usage:
• Reduce simulation speed
• Disable unnecessary visual effects
• Close other applications
• Check for background processes

High Memory Usage:
• Restart the application
• Reduce fleet size
• Clear export history
• Monitor for memory leaks

Slow Performance:
• Enable performance monitoring
• Check system resources
• Update graphics drivers
• Optimize simulation parameters"""
    
    def _get_analytics_content(self) -> str:
        return """Analytics and Predictive Modeling

CargoSim Advanced Features includes sophisticated analytics and predictive modeling capabilities to help you make data-driven decisions.

DEMAND FORECASTING
Predict resource demand at specific spokes:
• Select spoke location (S1-S15)
• Choose resource type (A, B, C, D)
• Set time horizon (1-168 hours)
• Get predicted demand with confidence scores
• View model accuracy and reliability

The forecasting system uses machine learning models trained on historical simulation data to predict future resource requirements.

COST PREDICTION
Estimate operation costs before execution:
• Operation types: flight, loading, unloading, maintenance
• Distance calculations in kilometers
• Aircraft type considerations
• Fuel price volatility modeling
• Maintenance cost projections

Cost predictions include confidence intervals and are based on current market conditions and historical cost data.

PERFORMANCE PREDICTION
Forecast system performance metrics:
• Operations per second trends
• Efficiency ratio projections
• Resource utilization forecasts
• Cost per operation predictions
• Performance degradation warnings

MODEL ACCURACY
All predictive models include:
• Confidence scores (0-100%)
• Model type identification
• Training data information
• Accuracy metrics
• Update timestamps

The analytics engine continuously improves predictions based on new data and user feedback."""
    
    def _get_export_integration_content(self) -> str:
        return """Data Export and Integration

CargoSim provides comprehensive data export capabilities and external system integration options.

EXPORT FORMATS
Supported export formats:
• CSV: Comma-separated values for spreadsheet analysis
• JSON: Structured data for programming and APIs
• Excel: Multi-sheet workbooks with formatting
• PDF: Professional reports with styling
• XML: Structured data for enterprise systems
• YAML: Human-readable configuration files

All exports include metadata and can be compressed for storage efficiency.

CLOUD STORAGE
Upload exports directly to cloud services:
• AWS S3: Amazon Simple Storage Service
• Google Cloud Storage: GCS integration
• Azure Blob Storage: Microsoft Azure support
• Custom endpoints: S3-compatible services

Features include:
• Automatic file naming
• Metadata tagging
• Compression support
• Upload verification
• Error handling and retry logic

DATABASE INTEGRATION
Connect to external databases:
• PostgreSQL: Primary supported database
• MySQL: Basic support available
• SQLite: Local database integration
• Custom drivers: Extensible architecture

Database features:
• Schema management
• Data validation
• Transaction support
• Connection pooling
• Security and authentication

API ENDPOINTS
RESTful API integration:
• Simulation data access
• Fleet management
• Cost analysis
• Performance metrics
• Real-time monitoring

API features:
• Authentication and authorization
• Rate limiting
• Request validation
• Response formatting
• Error handling"""
    
    def _get_troubleshooting_content(self) -> str:
        return """Troubleshooting Guide

This guide helps you resolve common issues with CargoSim Advanced Features.

COMMON ISSUES
Performance Monitoring Not Working:
• Check if psutil is installed
• Verify system permissions
• Restart the application
• Check system resource availability

Analytics Engine Errors:
• Ensure required packages are installed
• Check data validity and format
• Verify parameter ranges
• Review error logs for details

Export Failures:
• Check file permissions
• Verify disk space
• Ensure required packages are installed
• Check integration configurations

ERROR MESSAGES
"Performance monitor not available":
• Reinstall psutil package
• Check Python environment
• Restart application

"Analytics engine not available":
• Install required ML packages
• Check package versions
• Verify dependencies

"Export failed":
• Check file paths
• Verify permissions
• Ensure sufficient disk space
• Review error details

PERFORMANCE PROBLEMS
Slow GUI Response:
• Reduce update frequency
• Disable unnecessary features
• Check system resources
• Optimize simulation parameters

High Memory Usage:
• Clear export history
• Reduce fleet size
• Restart application
• Monitor for memory leaks

INTEGRATION ISSUES
Database Connection Failures:
• Verify connection parameters
• Check network connectivity
• Ensure database is running
• Verify credentials and permissions

Cloud Storage Issues:
• Check API keys and credentials
• Verify bucket permissions
• Check network connectivity
• Review service quotas

API Endpoint Problems:
• Verify endpoint URLs
• Check authentication tokens
• Test network connectivity
• Review API documentation

SOLUTIONS
General Troubleshooting Steps:
1. Check error messages and logs
2. Verify system requirements
3. Test with minimal configuration
4. Update packages and dependencies
5. Check system resources
6. Review configuration files
7. Test integrations individually
8. Consult online documentation"""
    
    def _get_advanced_configuration_content(self) -> str:
        return """Advanced Configuration

This section covers advanced configuration options for power users and system administrators.

PERFORMANCE TUNING
Monitoring Intervals:
• System metrics: 5 seconds (configurable)
• GUI updates: 2 seconds (configurable)
• Alert thresholds: Customizable
• History retention: Up to 1000 entries

Memory Management:
• Export history limits
• Cache size controls
• Garbage collection settings
• Memory leak detection

CUSTOM INTEGRATIONS
Webhook Configuration:
• Custom HTTP methods
• Header customization
• Authentication support
• Retry logic configuration

API Customization:
• Endpoint customization
• Response formatting
• Error handling
• Rate limiting

SECURITY SETTINGS
Authentication:
• API key management
• Credential encryption
• Access control lists
• Audit logging

Data Protection:
• Export encryption
• Secure transmission
• Access logging
• Privacy controls

BACKUP & RECOVERY
Configuration Backup:
• Automatic backup scheduling
• Version control
• Rollback capabilities
• Export/import functions

Data Recovery:
• Point-in-time recovery
• Incremental backups
• Verification tools
• Restoration procedures

ADVANCED FEATURES
Custom Metrics:
• User-defined performance metrics
• Custom alert thresholds
• Metric aggregation
• Trend analysis

Integration Extensions:
• Plugin architecture
• Custom exporters
• Third-party integrations
• API extensions

The advanced configuration options allow you to customize CargoSim for your specific needs while maintaining system stability and performance."""
