import PyPDF2

import zipfile
import xml.etree.ElementTree as ET
import os
from typing import List, AsyncGenerator, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import gc
import re

async def extract_text_streaming(file_path: str) -> AsyncGenerator[str, None]:
    """
    Stream text extraction from presentation files to handle large files.
    
    Args:
        file_path: Path to the presentation file
        
    Yields:
        str: Text chunks from the presentation (page by page or slide by slide)
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_ext == '.pdf':
            async for text_chunk in _extract_text_from_pdf_streaming(file_path):
                yield text_chunk
        elif file_ext in ['.pptx', '.ppt']:
            async for text_chunk in _extract_text_from_pptx_streaming(file_path):
                yield text_chunk
        else:
            raise Exception(f"Unsupported file type: {file_ext}")
    except Exception as e:
        raise Exception(f"Failed to extract text: {str(e)}")

async def _extract_text_from_pdf_streaming(file_path: str) -> AsyncGenerator[str, None]:
    """Extract text from PDF page by page to minimize memory usage."""
    
    def extract_page(file_path: str, page_num: int) -> str:
        """Extract text from a single PDF page."""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            if page_num < len(reader.pages):
                return reader.pages[page_num].extract_text()
        return ""
    
    # Get total page count first
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        total_pages = len(reader.pages)
    
    # Process pages one by one
    with ThreadPoolExecutor(max_workers=2) as executor:
        for page_num in range(total_pages):
            # Extract page text in thread to avoid blocking
            page_text = await asyncio.get_event_loop().run_in_executor(
                executor, extract_page, file_path, page_num
            )
            
            if page_text.strip():  # Only yield non-empty pages
                yield page_text
            
            # Allow other tasks to run
            await asyncio.sleep(0.001)

async def _extract_text_from_pptx_streaming(file_path: str) -> AsyncGenerator[str, None]:
    """
    Enhanced extract text from PPTX slide by slide using proper XML parsing
    to avoid loading entire file into memory.
    """
    
    def extract_slide_text(slide_xml: str) -> str:
        """Extract text from a single slide's XML."""
        try:
            # Register namespaces used in PPTX files
            namespaces = {
                'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
                'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'
            }

            root = ET.fromstring(slide_xml)
            texts = []
            
            # Look for text runs in the PPTX structure
            # Text is typically in <a:t> elements within text runs
            for t_elem in root.findall(".//a:t", namespaces):
                if t_elem and t_elem.text.strip():
                    texts.append(t_elem.text.strip())

            # Also check for direct text content in paragraphs
            for p_elem in root.findall('.//a:p', namespaces):
                for r_elem in p_elem.findall('.//a:r', namespaces):
                    for t_elem in r_elem.findall('.//a:t', namespaces):
                        if t_elem.text and t_elem.text.strip():
                            texts.append(t_elem.text.strip())

            return "\n".join(texts) if texts else ""
        except Exception as e:
            # Log the error but don't crash entire process
            print(f"Error extracting slide text: {e}")
            return ""
        
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            # Get list of slide files
            slide_files = [f for f in zip_file.namelist() 
                          if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
            slide_files.sort(key=lambda x: int(x.split('slide')[1].split('.')[0]))  # Sort numerically
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                for slide_file in slide_files:
                    try:
                        # Read slide XML
                        slide_xml = zip_file.read(slide_file).decode('utf-8')
                        
                        # Extract text in thread
                        slide_text = await asyncio.get_event_loop().run_in_executor(
                            executor, extract_slide_text, slide_xml
                        )
                        
                        if slide_text.strip():
                            yield slide_text
                        
                        # Allow other tasks to run and force garbage collection
                        await asyncio.sleep(0.001)
                        gc.collect()
                    except Exception as e:
                        print(f"Error processing slide {slide_file}: {e}")
                        continue

    except Exception as e:
        raise Exception(f"Failed to process PPTX file: {str(e)}")

async def chunk_text_streaming(
    text: str, 
    max_chunk_size: int = 1000, 
    overlap: int = 100
) -> AsyncGenerator[str, None]:
    """
    Stream text chunking to avoid memory spikes with large texts.
    Processes text in segments and yields chunks one by one.
    
    Args:
        text: Text to split into chunks
        max_chunk_size: Maximum size of each chunk in characters
        overlap: Number of characters to overlap between chunks
        
    Yields:
        str: Individual text chunks
    """

    def process_text_segment(text_segment: str, carry_over: List[str] = None) -> tuple[List[str], List[str]]:
        """
        Process a segment of text into chunks.
        
        Returns:
            tuple: (chunks, carry_over_sentences) where carry_over is for overlap with next segment
        """
        sentences = []

        #  Split on multiple sentence endings

        sentence_pattern = r'[.!?]+\s+'
        raw_sentences = re.split(sentence_pattern, text_segment.replace('\n', ' '))

        for i, sentence in enumerate(raw_sentences):
            if sentence.strip():
                # Add back the sentence ending (except the last one)
                if i < len(raw_sentences) - 1:
                    sentences.append(sentence.strip() + '+')
                else:
                    sentences.append(sentence.strip())
        
        # Add carry over from previous segment
        if carry_over:
            sentences = carry_over + sentences
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # If adding this sentence would exceed max size, save current chunk
            if current_size + sentence_size > max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # Keep last few sentences for overlap
                overlap_size = 0
                overlap_sentences = []
                for s in reversed(current_chunk):
                    if overlap_size + len(s) > overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_size += len(s)
                
                current_chunk = overlap_sentences
                current_size = overlap_size
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Return chunks and remaining sentences for next segment
        return chunks, current_chunk
  
    # Process text in smaller segments to avoid memory issues
    segment_size = max_chunk_size * 20  # Process 20 chunks worth at a time
    carry_over = []
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        for i in range(0, len(text), segment_size):
            text_segment = text[i:i + segment_size]
            
            # Process segment in thread to avoid blocking
            chunks, new_carry_over = await asyncio.get_event_loop().run_in_executor(
                executor, process_text_segment, text_segment, carry_over
            )
            
            # Yield all complete chunks from this segment
            for chunk in chunks:
                yield chunk
            
            # Keep carry over for next segment
            carry_over = new_carry_over
            
            # Allow other tasks to run and cleanup
            await asyncio.sleep(0.001)
            gc.collect()
        
        # Yield final chunk if there's remaining text
        if carry_over:
            final_chunk = ' '.join(carry_over)
            if final_chunk.strip():
                yield final_chunk


# Enhanced, utility function for batch processing
async def process_large_file_in_batches_with_metadata(
    file_path: str,
    presentation_id: int,
    batch_size: int = 50,
    max_chunk_size: int = 1000,
    overlap: int = 100
) -> AsyncGenerator[List[Dict[str, Any]], None]:
    """
    Process large files in batches with embedding service metadata.
    This version yields chunks with presentation_id and chunk_index.
    """
    current_batch = []
    chunk_index = 0
    
    async for text_segment in extract_text_streaming(file_path):
        async for chunk in chunk_text_streaming(text_segment, max_chunk_size, overlap):
            chunk_data = {
                "text": chunk,
                "chunk_index": chunk_index,
                "presentation_id": presentation_id
            }
            current_batch.append(chunk_data)
            chunk_index += 1            
            
            if len(current_batch) >= batch_size:
                yield current_batch
                current_batch = []
                gc.collect()  # Force cleanup between batches
    
    # Yield remaining chunks
    if current_batch:
        yield current_batch