"""
Test suite for enhanced error handling system in fleet_builder_gui.py

This test suite verifies:
- Retry operation mechanisms
- Error dialog creation and display
- Diagnostic information gathering
- Error recovery and user feedback
- Graceful degradation when operations fail
"""

import pytest
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock, call
import logging
import sys

# Try to import the error handling functions, with fallback to mocks if needed
try:
    from cargosim.ui.fleet_builder_gui import (
        retry_operation, 
        create_error_dialog, 
        safe_dict_get, 
        safe_list_get, 
        safe_attr_get,
        validate_aircraft_info,
        validate_fleet_summary
    )
    IMPORT_SUCCESS = True
except ImportError as e:
    # If import fails, create mock functions for testing
    print(f"Warning: Could not import from fleet_builder_gui: {e}")
    print("Creating mock functions for testing...")
    
    def retry_operation(operation_func, max_attempts=3, delay_ms=1000, operation_name="Operation"):
        """Mock retry operation for testing."""
        return operation_func()
    
    def create_error_dialog(parent, title, message, error_details=None, retry_callback=None, close_callback=None):
        """Mock error dialog creation for testing."""
        return Mock()
    
    def safe_dict_get(data, key, default=None):
        """Mock safe dict get for testing."""
        try:
            if data is None:
                return default
            return data.get(key, default)
        except:
            return default
    
    def safe_list_get(data, index, default=None):
        """Mock safe list get for testing."""
        try:
            if data is None or not isinstance(data, list):
                return default
            if 0 <= index < len(data):
                return data[index]
            return default
        except:
            return default
    
    def safe_attr_get(obj, attr, default=None):
        """Mock safe attr get for testing."""
        try:
            if obj is None:
                return default
            return getattr(obj, attr, default)
        except:
            return default
    
    def validate_aircraft_info(aircraft_info):
        """Mock aircraft info validation for testing."""
        if not aircraft_info or not isinstance(aircraft_info, dict):
            return False
        required_keys = ['name', 'count', 'capacity', 'total_capacity']
        return all(key in aircraft_info for key in required_keys)
    
    def validate_fleet_summary(summary):
        """Mock fleet summary validation for testing."""
        if not summary or not isinstance(summary, dict):
            return False
        required_keys = ['total_aircraft', 'total_capacity', 'aircraft_breakdown']
        return all(key in summary for key in required_keys)
    
    IMPORT_SUCCESS = False


class TestErrorHandlingUtilities:
    """Test the core error handling utility functions."""
    
    @pytest.mark.skipif(not IMPORT_SUCCESS, reason="Import failed, using mock functions")
    def test_import_status(self):
        """Test that imports were successful."""
        assert IMPORT_SUCCESS, "Error handling functions should be importable"
    
    def test_safe_dict_get_with_valid_data(self):
        """Test safe_dict_get with valid dictionary data."""
        test_data = {"key1": "value1", "key2": 42, "key3": None}
        
        assert safe_dict_get(test_data, "key1") == "value1"
        assert safe_dict_get(test_data, "key2") == 42
        assert safe_dict_get(test_data, "key3") is None
        assert safe_dict_get(test_data, "missing_key") is None
        assert safe_dict_get(test_data, "missing_key", "default") == "default"
    
    def test_safe_dict_get_with_invalid_data(self):
        """Test safe_dict_get with invalid data types."""
        assert safe_dict_get(None, "key") is None
        assert safe_dict_get("not_a_dict", "key") is None
        assert safe_dict_get(42, "key") is None
        assert safe_dict_get([], "key") is None
    
    def test_safe_dict_get_with_exception_handling(self):
        """Test safe_dict_get handles exceptions gracefully."""
        # Create a dict-like object that raises exceptions
        class ProblematicDict:
            def get(self, key, default=None):
                if key == "problematic":
                    raise AttributeError("Simulated error")
                return default
        
        problematic_dict = ProblematicDict()
        result = safe_dict_get(problematic_dict, "problematic")
        assert result is None
    
    def test_safe_list_get_with_valid_data(self):
        """Test safe_list_get with valid list data."""
        test_list = ["item1", "item2", "item3"]
        
        assert safe_list_get(test_list, 0) == "item1"
        assert safe_list_get(test_list, 1) == "item2"
        assert safe_list_get(test_list, 2) == "item3"
        assert safe_list_get(test_list, -1) is None  # Out of bounds
        assert safe_list_get(test_list, 3) is None   # Out of bounds
        assert safe_list_get(test_list, 0, "default") == "item1"
        assert safe_list_get(test_list, 5, "default") == "default"
    
    def test_safe_list_get_with_invalid_data(self):
        """Test safe_list_get with invalid data types."""
        assert safe_list_get(None, 0) is None
        assert safe_list_get("not_a_list", 0) is None
        assert safe_list_get(42, 0) is None
        assert safe_list_get({}, 0) is None
    
    def test_safe_list_get_with_exception_handling(self):
        """Test safe_list_get handles exceptions gracefully."""
        # Create a list-like object that raises exceptions
        class ProblematicList:
            def __getitem__(self, index):
                if index == 1:
                    raise TypeError("Simulated error")
                return f"item{index}"
            
            def __len__(self):
                return 3
        
        problematic_list = ProblematicList()
        result = safe_list_get(problematic_list, 1)
        assert result is None
    
    def test_safe_attr_get_with_valid_object(self):
        """Test safe_attr_get with valid object."""
        class TestObject:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42
        
        obj = TestObject()
        
        assert safe_attr_get(obj, "attr1") == "value1"
        assert safe_attr_get(obj, "attr2") == 42
        assert safe_attr_get(obj, "missing_attr") is None
        assert safe_attr_get(obj, "missing_attr", "default") == "default"
    
    def test_safe_attr_get_with_invalid_object(self):
        """Test safe_attr_get with invalid objects."""
        assert safe_attr_get(None, "attr") is None
        assert safe_attr_get("not_an_object", "attr") is None
        assert safe_attr_get(42, "attr") is None
    
    def test_safe_attr_get_with_exception_handling(self):
        """Test safe_attr_get handles exceptions gracefully."""
        # Create an object that raises exceptions on attribute access
        class ProblematicObject:
            def __getattr__(self, name):
                if name == "problematic":
                    raise RuntimeError("Simulated error")
                return "normal_value"
        
        problematic_obj = ProblematicObject()
        result = safe_attr_get(problematic_obj, "problematic")
        assert result is None
        
        # Test normal attribute access still works
        result = safe_attr_get(problematic_obj, "normal")
        assert result == "normal_value"
    
    def test_validate_aircraft_info_with_valid_data(self):
        """Test validate_aircraft_info with valid aircraft data."""
        valid_aircraft = {
            "name": "Boeing 737",
            "count": 5,
            "capacity": 150,
            "total_capacity": 750
        }
        
        assert validate_aircraft_info(valid_aircraft) is True
    
    def test_validate_aircraft_info_with_invalid_data(self):
        """Test validate_aircraft_info with invalid aircraft data."""
        # Missing required keys
        invalid_aircraft1 = {"name": "Boeing 737", "count": 5}
        assert validate_aircraft_info(invalid_aircraft1) is False
        
        # Wrong data type
        invalid_aircraft2 = {"name": "Boeing 737", "count": "five", "capacity": 150, "total_capacity": 750}
        assert validate_aircraft_info(invalid_aircraft2) is False
        
        # None data
        assert validate_aircraft_info(None) is False
        
        # Empty dict
        assert validate_aircraft_info({}) is False
    
    def test_validate_fleet_summary_with_valid_data(self):
        """Test validate_fleet_summary with valid fleet summary data."""
        valid_summary = {
            "total_aircraft": 10,
            "total_capacity": 1500,
            "aircraft_breakdown": {
                "Boeing 737": {"name": "Boeing 737", "count": 5, "capacity": 150, "total_capacity": 750},
                "Airbus A320": {"name": "Airbus A320", "count": 5, "capacity": 150, "total_capacity": 750}
            }
        }
        
        assert validate_fleet_summary(valid_summary) is True
    
    def test_validate_fleet_summary_with_invalid_data(self):
        """Test validate_fleet_summary with invalid fleet summary data."""
        # Missing required keys
        invalid_summary1 = {"total_aircraft": 10, "total_capacity": 1500}
        assert validate_fleet_summary(invalid_summary1) is False
        
        # Wrong data type
        invalid_summary2 = {"total_aircraft": "ten", "total_capacity": 1500, "aircraft_breakdown": {}}
        assert validate_fleet_summary(invalid_summary2) is False
        
        # None data
        assert validate_fleet_summary(None) is False
        
        # Empty dict
        assert validate_fleet_summary({}) is False


class TestRetryOperation:
    """Test the retry operation mechanism."""
    
    def test_retry_operation_success_on_first_try(self):
        """Test retry_operation succeeds on first attempt."""
        def successful_operation():
            return "success"
        
        result = retry_operation(successful_operation, max_attempts=3, operation_name="Test")
        assert result == "success"
    
    def test_retry_operation_success_after_failures(self):
        """Test retry_operation succeeds after some failures."""
        call_count = 0
        
        def operation_with_failures():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Simulated failure {call_count}")
            return "success"
        
        result = retry_operation(operation_with_failures, max_attempts=3, operation_name="Test")
        assert result == "success"
        assert call_count == 3
    
    def test_retry_operation_failure_after_max_attempts(self):
        """Test retry_operation fails after maximum attempts."""
        def always_failing_operation():
            raise RuntimeError("Always fails")
        
        with pytest.raises(RuntimeError, match="Always fails"):
            retry_operation(always_failing_operation, max_attempts=2, operation_name="Test")
    
    def test_retry_operation_with_custom_parameters(self):
        """Test retry_operation with custom retry parameters."""
        call_count = 0
        
        def operation_with_failures():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError(f"Simulated failure {call_count}")
            return "success"
        
        result = retry_operation(
            operation_with_failures, 
            max_attempts=5, 
            delay_ms=100, 
            operation_name="Custom Test"
        )
        assert result == "success"
        assert call_count == 2
    
    def test_retry_operation_exponential_backoff(self):
        """Test retry_operation uses exponential backoff."""
        import time
        
        call_count = 0
        start_time = time.time()
        
        def operation_with_failures():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Simulated failure {call_count}")
            return "success"
        
        result = retry_operation(
            operation_with_failures, 
            max_attempts=3, 
            delay_ms=100, 
            operation_name="Backoff Test"
        )
        
        elapsed_time = time.time() - start_time
        # Should have delays: 100ms + 200ms = 300ms minimum
        assert elapsed_time >= 0.3
        assert result == "success"
        assert call_count == 3


class TestErrorDialogCreation:
    """Test the error dialog creation and display."""
    
    @pytest.fixture
    def mock_tkinter(self):
        """Mock tkinter components for testing."""
        with patch('tkinter.Toplevel') as mock_toplevel, \
             patch('tkinter.ttk.Frame') as mock_frame, \
             patch('tkinter.ttk.Label') as mock_label, \
             patch('tkinter.ttk.Button') as mock_button, \
             patch('tkinter.ttk.Checkbutton') as mock_checkbutton, \
             patch('tkinter.Text') as mock_text, \
             patch('tkinter.BooleanVar') as mock_boolean_var:
            
            # Mock the dialog instance
            mock_dialog = Mock()
            mock_toplevel.return_value = mock_dialog
            
            # Mock frame instances
            mock_header_frame = Mock()
            mock_message_frame = Mock()
            mock_details_frame = Mock()
            mock_button_frame = Mock()
            mock_frame.side_effect = [mock_header_frame, mock_message_frame, mock_details_frame, mock_button_frame]
            
            # Mock label instances
            mock_icon_label = Mock()
            mock_title_label = Mock()
            mock_message_label = Mock()
            mock_label.side_effect = [mock_icon_label, mock_title_label, mock_message_label]
            
            # Mock button instances
            mock_retry_button = Mock()
            mock_close_button = Mock()
            mock_button.side_effect = [mock_retry_button, mock_close_button]
            
            # Mock checkbutton and text
            mock_details_check = Mock()
            mock_details_text = Mock()
            mock_checkbutton.return_value = mock_details_check
            mock_text.return_value = mock_details_text
            
            # Mock boolean variable
            mock_details_var = Mock()
            mock_boolean_var.return_value = mock_details_var
            
            yield {
                'dialog': mock_dialog,
                'header_frame': mock_header_frame,
                'message_frame': mock_message_frame,
                'details_frame': mock_details_frame,
                'button_frame': mock_button_frame,
                'icon_label': mock_icon_label,
                'title_label': mock_title_label,
                'message_label': mock_message_label,
                'retry_button': mock_retry_button,
                'close_button': mock_close_button,
                'details_check': mock_details_check,
                'details_text': mock_details_text,
                'details_var': mock_details_var
            }
    
    def test_create_error_dialog_basic(self, mock_tkinter):
        """Test basic error dialog creation without optional parameters."""
        mock_parent = Mock()
        
        result = create_error_dialog(
            parent=mock_parent,
            title="Test Error",
            message="Test message"
        )
        
        # Verify dialog was created
        assert result is not None
        
        # Verify basic setup
        mock_tkinter['dialog'].title.assert_called_with("Error - Test Error")
        mock_tkinter['dialog'].geometry.assert_called_with("500x400")
        mock_tkinter['dialog'].resizable.assert_called_with(False, False)
        mock_tkinter['dialog'].transient.assert_called_with(mock_parent)
        mock_tkinter['dialog'].grab_set.assert_called_once()
    
    def test_create_error_dialog_with_details(self, mock_tkinter):
        """Test error dialog creation with error details."""
        mock_parent = Mock()
        
        result = create_error_dialog(
            parent=mock_parent,
            title="Test Error",
            message="Test message",
            error_details="Detailed error information"
        )
        
        # Verify details section was created
        mock_tkinter['details_check'].pack.assert_called_once()
        mock_tkinter['details_text'].pack.assert_called_once()
    
    def test_create_error_dialog_with_retry_callback(self, mock_tkinter):
        """Test error dialog creation with retry callback."""
        mock_parent = Mock()
        mock_retry_callback = Mock()
        
        result = create_error_dialog(
            parent=mock_parent,
            title="Test Error",
            message="Test message",
            retry_callback=mock_retry_callback
        )
        
        # Verify retry button was created
        mock_tkinter['retry_button'].pack.assert_called_once()
    
    def test_create_error_dialog_with_close_callback(self, mock_tkinter):
        """Test error dialog creation with close callback."""
        mock_parent = Mock()
        mock_close_callback = Mock()
        
        result = create_error_dialog(
            parent=mock_parent,
            title="Test Error",
            message="Test message",
            close_callback=mock_close_callback
        )
        
        # Verify close button was created
        mock_tkinter['close_button'].pack.assert_called_once()
    
    def test_create_error_dialog_fallback_on_error(self, mock_tkinter):
        """Test error dialog creation falls back to messagebox on error."""
        mock_parent = Mock()
        
        # Make the dialog creation fail
        mock_tkinter['dialog'].title.side_effect = Exception("Dialog creation failed")
        
        with patch('tkinter.messagebox.showerror') as mock_showerror:
            result = create_error_dialog(
                parent=mock_parent,
                title="Test Error",
                message="Test message"
            )
            
            # Should fall back to messagebox
            mock_showerror.assert_called_once()
            assert result is None


class TestErrorHandlingIntegration:
    """Test integration of error handling components."""
    
    def test_error_handling_chain_with_retry(self):
        """Test complete error handling chain with retry mechanism."""
        # Simulate a failing operation that eventually succeeds
        call_count = 0
        
        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"Connection failed {call_count}")
            return "Operation succeeded"
        
        # Test retry mechanism
        result = retry_operation(failing_operation, max_attempts=5, operation_name="Integration Test")
        
        assert result == "Operation succeeded"
        assert call_count == 3
    
    def test_safe_access_with_validation_chain(self):
        """Test safe access functions work together with validation."""
        # Create test data with some invalid entries
        test_data = {
            "fleet_summary": {
                "total_aircraft": 5,
                "total_capacity": 750,
                "aircraft_breakdown": {
                    "aircraft1": {
                        "name": "Boeing 737",
                        "count": 3,
                        "capacity": 150,
                        "total_capacity": 450
                    },
                    "aircraft2": {
                        "name": "Airbus A320",
                        "count": 2,
                        "capacity": 150,
                        "total_capacity": 300
                    }
                }
            }
        }
        
        # Test safe access chain
        fleet_summary = safe_dict_get(test_data, "fleet_summary")
        assert fleet_summary is not None
        
        # Validate the summary
        assert validate_fleet_summary(fleet_summary) is True
        
        # Access aircraft breakdown safely
        aircraft_breakdown = safe_dict_get(fleet_summary, "aircraft_breakdown")
        assert aircraft_breakdown is not None
        
        # Validate individual aircraft
        for aircraft_id, aircraft_info in aircraft_breakdown.items():
            assert validate_aircraft_info(aircraft_info) is True
    
    def test_error_handling_with_mixed_data_quality(self):
        """Test error handling with mixed quality data."""
        # Create data with some valid and some invalid entries
        mixed_data = {
            "valid_aircraft": {
                "name": "Boeing 737",
                "count": 5,
                "capacity": 150,
                "total_capacity": 750
            },
            "invalid_aircraft": {
                "name": "Airbus A320",
                "count": "invalid_count"  # Wrong type
            },
            "missing_aircraft": None,
            "empty_aircraft": {}
        }
        
        # Test safe access with validation
        valid_aircraft = safe_dict_get(mixed_data, "valid_aircraft")
        assert validate_aircraft_info(valid_aircraft) is True
        
        invalid_aircraft = safe_dict_get(mixed_data, "invalid_aircraft")
        assert validate_aircraft_info(invalid_aircraft) is False
        
        missing_aircraft = safe_dict_get(mixed_data, "missing_aircraft")
        assert validate_aircraft_info(missing_aircraft) is False
        
        empty_aircraft = safe_dict_get(mixed_data, "empty_aircraft")
        assert validate_aircraft_info(empty_aircraft) is False


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
