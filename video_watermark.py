import logging
import asyncio
import ffmpeg
import os
import tempfile
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class VideoWatermarker:
    """Add moving watermark to videos with DVD bouncing effect"""

    def __init__(self, watermark_text: str):
        """
        Args:
            watermark_text: Text to use as watermark
        """
        self.watermark_text = watermark_text

    async def add_moving_watermark(
            self,
            input_path: str,
            output_path: Optional[str] = None,
            font_size: int = 24,
            font_color: str = 'white',
            box_color: str = 'black@0.5',
            speed: int = 2
    ) -> Optional[str]:
        """
        Add bouncing watermark to video (DVD screensaver style).

        Args:
            input_path: Path to input video
            output_path: Path to output video (if None, creates temp file)
            font_size: Font size for watermark
            font_color: Color of the text
            box_color: Background box color (format: color@opacity)
            speed: Movement speed (pixels per frame, default 2)

        Returns:
            Path to watermarked video or None if failed
        """
        try:
            if output_path is None:
                # Create temporary output file
                fd, output_path = tempfile.mkstemp(suffix='.mp4', prefix='watermarked_')
                os.close(fd)

            logger.info(f"Adding moving watermark to video: {input_path}")

            # Run ffmpeg in thread pool (it's CPU-intensive)
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._add_watermark_sync,
                input_path,
                output_path,
                font_size,
                font_color,
                box_color,
                speed
            )

            if result:
                logger.info(f"Watermarked video saved to: {output_path}")
                return output_path
            else:
                return None

        except Exception as e:
            logger.error(f"Error adding moving watermark: {e}")
            # Clean up output file if it exists
            if output_path and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            return None

    def _add_watermark_sync(
            self,
            input_path: str,
            output_path: str,
            font_size: int,
            font_color: str,
            box_color: str,
            speed: int
    ) -> bool:
        """Synchronous watermarking function to run in thread pool"""
        try:
            # Get video info first
            probe = ffmpeg.probe(input_path)
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            width = int(video_info['width'])
            height = int(video_info['height'])

            logger.info(f"Video dimensions: {width}x{height}")

            # Calculate watermark dimensions (approximate)
            # Each character is roughly font_size/2 in width
            text_width = len(self.watermark_text) * (font_size // 2)
            text_height = font_size + 10  # Add some padding

            # Calculate bounce boundaries
            max_x = width - text_width - 20  # 20px padding
            max_y = height - text_height - 20

            # Ensure boundaries are positive
            if max_x < 20:
                max_x = 20
            if max_y < 20:
                max_y = 20

            # DVD bouncing effect using ffmpeg expressions
            # The idea: x and y positions oscillate between boundaries
            # We use mod to create a sawtooth wave, then conditionally reverse it
            #
            # Formula explanation:
            # - n*speed creates linear movement based on frame number
            # - mod(n*speed, 2*max) creates a repeating pattern from 0 to 2*max
            # - if(gte(mod(...), max), 2*max - mod(...), mod(...)) creates bouncing:
            #   - When value >= max: move backward (2*max - value)
            #   - When value < max: move forward (value)

            x_expr = f"if(gte(mod(n*{speed}, {2*max_x}), {max_x}), {2*max_x}-mod(n*{speed}, {2*max_x}), mod(n*{speed}, {2*max_x}))+10"
            y_expr = f"if(gte(mod(n*{speed}*0.7, {2*max_y}), {max_y}), {2*max_y}-mod(n*{speed}*0.7, {2*max_y}), mod(n*{speed}*0.7, {2*max_y}))+10"

            # Note: Using 0.7 multiplier for y to create different speeds on x and y axes
            # This makes the movement more interesting (not just diagonal)

            # Build ffmpeg filter
            # drawtext filter creates the text overlay with moving position
            drawtext_filter = (
                f"drawtext="
                f"text='{self.watermark_text}':"
                f"fontsize={font_size}:"
                f"fontcolor={font_color}:"
                f"box=1:"
                f"boxcolor={box_color}:"
                f"boxborderw=5:"
                f"x={x_expr}:"
                f"y={y_expr}"
            )

            logger.info(f"Applying filter: {drawtext_filter}")

            # Run ffmpeg
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.filter(stream, 'drawtext',
                                   text=self.watermark_text,
                                   fontsize=font_size,
                                   fontcolor=font_color,
                                   box=1,
                                   boxcolor=box_color,
                                   boxborderw=5,
                                   x=x_expr,
                                   y=y_expr)
            stream = ffmpeg.output(stream, output_path,
                                   vcodec='libx264',
                                   acodec='copy',  # Copy audio without re-encoding
                                   preset='medium',  # Balance between speed and quality
                                   crf=23)  # Quality factor (lower = better quality)

            # Run with overwrite and capture output
            ffmpeg.run(stream, overwrite_output=True, quiet=False, capture_stdout=True, capture_stderr=True)

            logger.info("Watermark added successfully")
            return True

        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error in _add_watermark_sync: {e}")
            return False

    async def add_static_watermark(
            self,
            input_path: str,
            output_path: Optional[str] = None,
            font_size: int = 24,
            position: str = 'bottom_right'
    ) -> Optional[str]:
        """
        Add static watermark to video (simpler, less CPU-intensive).

        Args:
            input_path: Path to input video
            output_path: Path to output video (if None, creates temp file)
            font_size: Font size for watermark
            position: Position ('bottom_right', 'bottom_left', 'top_right', 'top_left')

        Returns:
            Path to watermarked video or None if failed
        """
        try:
            if output_path is None:
                fd, output_path = tempfile.mkstemp(suffix='.mp4', prefix='watermarked_')
                os.close(fd)

            logger.info(f"Adding static watermark to video: {input_path}")

            # Position mapping
            position_map = {
                'bottom_right': 'x=w-tw-10:y=h-th-10',
                'bottom_left': 'x=10:y=h-th-10',
                'top_right': 'x=w-tw-10:y=10',
                'top_left': 'x=10:y=10',
            }

            xy_expr = position_map.get(position, position_map['bottom_right'])

            # Run ffmpeg in thread pool
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._add_static_watermark_sync,
                input_path,
                output_path,
                font_size,
                xy_expr
            )

            if result:
                logger.info(f"Watermarked video saved to: {output_path}")
                return output_path
            else:
                return None

        except Exception as e:
            logger.error(f"Error adding static watermark: {e}")
            if output_path and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            return None

    def _add_static_watermark_sync(
            self,
            input_path: str,
            output_path: str,
            font_size: int,
            xy_expr: str
    ) -> bool:
        """Synchronous static watermarking"""
        try:
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.filter(stream, 'drawtext',
                                   text=self.watermark_text,
                                   fontsize=font_size,
                                   fontcolor='white',
                                   box=1,
                                   boxcolor='black@0.5',
                                   boxborderw=5,
                                   x=xy_expr.split(':')[0].split('=')[1],
                                   y=xy_expr.split(':')[1].split('=')[1])
            stream = ffmpeg.output(stream, output_path,
                                   vcodec='libx264',
                                   acodec='copy',
                                   preset='medium',
                                   crf=23)

            ffmpeg.run(stream, overwrite_output=True, quiet=False, capture_stdout=True, capture_stderr=True)
            return True

        except Exception as e:
            logger.error(f"Error in _add_static_watermark_sync: {e}")
            return False

    @staticmethod
    def cleanup_file(file_path: str):
        """Clean up temporary file"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {e}")
