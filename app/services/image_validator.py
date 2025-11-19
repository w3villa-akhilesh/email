import os
from pathlib import Path
from typing import Tuple
from PIL import Image
from app.utils.logger import logger

class ImageValidator:
    """
    Image validation and compression service
    Supports PNG, JPEG/JPG, WebP, and GIF formats
    """
    
    SUPPORTED_MIME_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif']
    SUPPORTED_EXTENSIONS = ['.png', '.jpeg', '.jpg', '.webp', '.gif']
    USE_ORIGINAL_MARKER = "USE_ORIGINAL"
        
    def is_image_type_valid(self, content_type: str, filename: str) -> Tuple[bool, str]:
        """
        Check if the image type is valid
        
        Args:
            content_type: MIME type of the file
            filename: Name of the file
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not content_type or content_type not in self.SUPPORTED_MIME_TYPES:
            return False, f"Invalid file type: {content_type}. Only PNG, JPEG/JPG, WebP, and GIF files are supported."
        
        if filename:
            file_extension = Path(filename).suffix.lower()
            if file_extension not in self.SUPPORTED_EXTENSIONS:
                return False, f"Invalid file extension: {file_extension}. Only .png, .jpeg, .jpg, .webp, and .gif extensions are supported."
        
        return True, ""
    
    def get_file_size_mb(self, file_path: str) -> float:
        """Get file size in MB"""
        try:
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            return round(size_mb, 2)
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return 0.0
    
    def _convert_rgba_to_rgb(self, img: Image.Image) -> Image.Image:
        """Convert RGBA/LA image to RGB with white background"""
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            return background
        return img
    
    def compress_image(self, input_path: str, output_path: str, quality: int) -> Tuple[bool, str, float, float]:
        """
        Compress image using Pillow
        
        Args:
            input_path: Path to input image
            output_path: Path to save compressed image
            quality: Compression quality (1-100)
            
        Returns:
            Tuple[bool, str, float, float]: (success, error_message, original_size_mb, compressed_size_mb)
        """
        try:
            # Get original file size
            original_size_mb = self.get_file_size_mb(input_path)
            
            # Open and process image
            with Image.open(input_path) as img:
                # Determine format and save with compression
                file_extension = Path(input_path).suffix.lower()
                
                if file_extension in ['.jpg', '.jpeg']:
                    # Convert RGBA to RGB for JPEG (doesn't support transparency)
                    img = self._convert_rgba_to_rgb(img)
                    img.save(output_path, 'JPEG', quality=quality, optimize=True)
                elif file_extension == '.png':
                    # PNG: Use moderate compression to avoid size increase
                    img.save(output_path, 'PNG', optimize=True, compress_level=6)
                elif file_extension == '.webp':
                    img.save(output_path, 'WebP', quality=quality, optimize=True)
                elif file_extension == '.gif':
                    img.save(output_path, 'GIF', optimize=True)
                else:
                    # Default to JPEG for unknown formats
                    img = self._convert_rgba_to_rgb(img)
                    img.save(output_path, 'JPEG', quality=quality, optimize=True)
            
            # Get compressed file size
            compressed_size_mb = self.get_file_size_mb(output_path)
            
            # If compression increased file size, use original file instead
            if compressed_size_mb >= original_size_mb:
                logger.warning(f"Compression increased file size: {original_size_mb}MB → {compressed_size_mb}MB. Using original file.")
                # Remove the compressed file and return original info
                if os.path.exists(output_path):
                    os.remove(output_path)
                # Return special marker to indicate original file should be used
                return True, self.USE_ORIGINAL_MARKER, original_size_mb, original_size_mb
            
            logger.info(f"Image compressed: {original_size_mb}MB → {compressed_size_mb}MB (Quality: {quality}%)")
            
            return True, "", original_size_mb, compressed_size_mb
            
        except Exception as e:
            error_msg = f"Error compressing image: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, 0.0, 0.0
    
    def validate_and_process_image(self, file_path: str, content_type: str, filename: str) -> Tuple[bool, str, str]:
        """
        Validate image type and process/compress if needed
        - Rejects files larger than 10MB
        - Skips compression for files smaller than 1MB
        - Compresses files 1-10MB based on size
        
        Args:
            file_path: Path to the image file
            content_type: MIME type of the file
            filename: Original filename
            
        Returns:
            Tuple[bool, str, str]: (success, error_message, processed_file_path)
        """
        try:
            # Step 1: Validate image type
            is_valid, error_msg = self.is_image_type_valid(content_type, filename)
            if not is_valid:
                return False, error_msg, file_path
            
            # Step 2: Check file size and reject if > 5MB before compression
            original_size_mb = self.get_file_size_mb(file_path)
            logger.info(f"Original image size: {original_size_mb}MB")
            
            # Check if file is too large before attempting compression
            if original_size_mb > 10.0:
                error_msg = f"Image file too large: {original_size_mb}MB. Maximum allowed size is 10MB"
                logger.error(error_msg)
                return False, error_msg, file_path
            
            # Skip compression for files smaller than 1MB
            if original_size_mb < 1.0:
                logger.info(f"Image size < 1MB: No compression needed")
                logger.info(f"Image validation and processing completed successfully")
                return True, "", file_path
            
            # Determine compression strategy for files 1-10MB
            if original_size_mb < 2.0:
                # Compress to 30% quality for files 1-2MB
                quality = 30
                logger.info(f"Image size 1-2MB: Compressing to {quality}% quality")
            elif original_size_mb < 5.0:
                # Compress to 20% quality for files 2-5MB
                quality = 20
                logger.info(f"Image size 2-5MB: Compressing to {quality}% quality")
            else:
                # Compress to 15% quality for files 5-10MB
                quality = 15
                logger.info(f"Image size 5-10MB: Compressing to {quality}% quality")
            
            # Create output path for compressed image
            file_path_obj = Path(file_path)
            compressed_file_path = str(file_path_obj.parent / f"compressed_{file_path_obj.name}")
            
            # Compress the image
            success, error_msg, original_size, compressed_size = self.compress_image(
                file_path, compressed_file_path, quality
            )
            
            if not success:
                return False, error_msg, file_path
            
            # Determine which file to use
            final_file_path = compressed_file_path if compressed_size < original_size else file_path
            
            logger.info(f"Image validation and processing completed successfully")
            if compressed_size < original_size:
                logger.info(f"Size reduction: {original_size}MB → {compressed_size}MB ({((original_size - compressed_size) / original_size * 100):.1f}% reduction)")
            else:
                logger.info(f"Using original file (compression would have increased size)")
            
            return True, "", final_file_path
            
        except Exception as e:
            error_msg = f"Error validating and processing image: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, file_path

# Create global instance
image_validator = ImageValidator()
