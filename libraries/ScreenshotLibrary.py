"""
Screenshot library for capturing test evidence.

This library creates visual evidence for test execution by generating
screenshots at key points in the test flow.
"""

import os
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont


class ScreenshotLibrary:
    """Library for capturing screenshots during test execution."""
    
    ROBOT_LIBRARY_SCOPE = 'TEST'
    
    def __init__(self):
        """Initialize the screenshot library."""
        self.screenshot_dir = Path("output/screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_counter = 0
        self.current_test_screenshots = []
    
    def capture_screenshot(self, name: str, width: int = 800, height: int = 600) -> str:
        """
        Capture a screenshot with the given name.
        
        Args:
            name: Name/description for the screenshot
            width: Screenshot width in pixels
            height: Screenshot height in pixels
            
        Returns:
            Path to the screenshot file
        """
        self.screenshot_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{self.screenshot_counter}_{timestamp}_{self._sanitize_name(name)}.png"
        filepath = self.screenshot_dir / filename
        
        # Create a mock screenshot (in real scenario, this would capture actual UI)
        self._create_mock_screenshot(filepath, name, width, height)
        
        # Track screenshot for current test
        self.current_test_screenshots.append(str(filepath))
        
        print(f"📸 Screenshot captured: {filepath}")
        return str(filepath)
    
    def capture_page_screenshot(self, page_name: str) -> str:
        """
        Capture a screenshot of a page.
        
        Args:
            page_name: Name of the page (e.g., "Login Page", "Dashboard")
            
        Returns:
            Path to the screenshot file
        """
        return self.capture_screenshot(f"{page_name}", 800, 600)
    
    def capture_element_screenshot(self, element_name: str) -> str:
        """
        Capture a screenshot highlighting an element.
        
        Args:
            element_name: Name of the element (e.g., "Login Button", "Error Message")
            
        Returns:
            Path to the screenshot file
        """
        return self.capture_screenshot(f"Element - {element_name}", 800, 600)
    
    def get_test_screenshots(self) -> list:
        """
        Get all screenshots captured for the current test.
        
        Returns:
            List of screenshot file paths
        """
        return self.current_test_screenshots.copy()
    
    def clear_test_screenshots(self):
        """Clear the list of screenshots for the current test."""
        self.current_test_screenshots = []
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize filename by removing invalid characters."""
        return "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip()
    
    def _create_mock_screenshot(self, filepath: Path, title: str, width: int, height: int):
        """
        Create a mock screenshot for demonstration.
        
        In a real implementation, this would capture actual browser/UI screenshots.
        """
        # Create a simple image with title
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw border
        draw.rectangle([(0, 0), (width-1, height-1)], outline='#2c3e50', width=3)
        
        # Draw header
        draw.rectangle([(0, 0), (width, 60)], fill='#3498db')
        
        # Try to load a font, fallback to default
        try:
            font_title = ImageFont.truetype("arial.ttf", 24)
            font_body = ImageFont.truetype("arial.ttf", 16)
        except:
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()
        
        # Draw title
        title_text = title[:50]  # Truncate long titles
        draw.text((20, 20), title_text, fill='white', font=font_title)
        
        # Draw timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        draw.text((20, 80), f"Captured: {timestamp}", fill='#2c3e50', font=font_body)
        
        # Draw content area
        content_y = 120
        draw.rectangle([(20, content_y), (width-20, height-80)], outline='#bdc3c7', width=2)
        
        # Add some mock content based on title
        if "login" in title.lower():
            draw.text((40, content_y + 20), "Username: [________]", fill='#34495e', font=font_body)
            draw.text((40, content_y + 60), "Password: [________]", fill='#34495e', font=font_body)
            draw.rectangle([(40, content_y + 100), (150, content_y + 140)], fill='#2ecc71')
            draw.text((60, content_y + 110), "Login", fill='white', font=font_body)
        elif "dashboard" in title.lower():
            draw.text((40, content_y + 20), "Welcome to Dashboard", fill='#2c3e50', font=font_title)
            draw.text((40, content_y + 60), "User: testuser", fill='#34495e', font=font_body)
            draw.text((40, content_y + 90), "Last Login: " + timestamp, fill='#34495e', font=font_body)
        elif "error" in title.lower() or "invalid" in title.lower():
            draw.rectangle([(20, content_y + 20), (width-20, content_y + 80)], fill='#e74c3c')
            draw.text((40, content_y + 35), "❌ Invalid Credentials", fill='white', font=font_body)
            draw.text((40, content_y + 55), "Please try again", fill='white', font=font_body)
        elif "success" in title.lower():
            draw.rectangle([(20, content_y + 20), (width-20, content_y + 80)], fill='#2ecc71')
            draw.text((40, content_y + 35), "✓ Success!", fill='white', font=font_body)
            draw.text((40, content_y + 55), "Operation completed successfully", fill='white', font=font_body)
        else:
            draw.text((40, content_y + 20), f"Screenshot: {title}", fill='#34495e', font=font_body)
        
        # Draw footer
        draw.text((20, height - 40), "Automated Test Screenshot", fill='#7f8c8d', font=font_body)
        
        # Save the image
        img.save(filepath, 'PNG')
