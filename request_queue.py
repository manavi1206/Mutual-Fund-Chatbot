"""
Request Queue - Async request processing with queue management
Enterprise-grade request handling
"""
from asyncio import Queue, create_task, sleep
from typing import Dict, Optional, Callable, Any
import time
from collections import deque


class RequestQueue:
    """Manages request queue for async processing"""
    
    def __init__(self, max_size: int = 50, num_workers: int = 3):
        """
        Initialize request queue
        
        Args:
            max_size: Maximum queue size
            num_workers: Number of background workers
        """
        self.queue = Queue(maxsize=max_size)
        self.num_workers = num_workers
        self.workers = []
        self.is_running = False
        self.stats = {
            'total_processed': 0,
            'total_failed': 0,
            'queue_size': 0,
            'avg_processing_time': 0.0
        }
        self.processing_times = deque(maxlen=100)
    
    async def start_workers(self):
        """Start background worker tasks"""
        if self.is_running:
            return
        
        self.is_running = True
        for i in range(self.num_workers):
            worker = create_task(self._worker(f"worker-{i+1}"))
            self.workers.append(worker)
    
    async def stop_workers(self):
        """Stop background workers"""
        self.is_running = False
        # Wait for queue to empty
        await self.queue.join()
        # Cancel workers
        for worker in self.workers:
            worker.cancel()
        self.workers = []
    
    async def _worker(self, worker_name: str):
        """Background worker that processes queue items"""
        while self.is_running:
            try:
                item = await self.queue.get()
                start_time = time.time()
                
                try:
                    # Process the item
                    result = await item['processor'](*item.get('args', []), **item.get('kwargs', {}))
                    
                    # Call callback with result
                    if item.get('callback'):
                        await item['callback'](result)
                    
                    processing_time = time.time() - start_time
                    self.processing_times.append(processing_time)
                    self.stats['total_processed'] += 1
                    
                except Exception as e:
                    self.stats['total_failed'] += 1
                    if item.get('error_callback'):
                        await item['error_callback'](e)
                    else:
                        print(f"⚠️  {worker_name}: Error processing item: {e}")
                
                finally:
                    self.queue.task_done()
                    self.stats['queue_size'] = self.queue.qsize()
                    
            except Exception as e:
                print(f"⚠️  {worker_name}: Worker error: {e}")
                await sleep(1)
    
    async def enqueue(self, processor: Callable, callback: Optional[Callable] = None,
                     error_callback: Optional[Callable] = None, *args, **kwargs) -> bool:
        """
        Enqueue a request for processing
        
        Args:
            processor: Async function to process the request
            callback: Optional callback when processing succeeds
            error_callback: Optional callback when processing fails
            *args, **kwargs: Arguments for processor
            
        Returns:
            True if enqueued, False if queue is full
        """
        if not self.is_running:
            await self.start_workers()
        
        try:
            item = {
                'processor': processor,
                'callback': callback,
                'error_callback': error_callback,
                'args': args,
                'kwargs': kwargs,
                'enqueued_at': time.time()
            }
            await self.queue.put(item)
            self.stats['queue_size'] = self.queue.qsize()
            return True
        except Exception:
            # Queue is full
            return False
    
    def get_stats(self) -> Dict:
        """Get queue statistics"""
        if self.processing_times:
            self.stats['avg_processing_time'] = sum(self.processing_times) / len(self.processing_times)
        
        return {
            **self.stats,
            'queue_size': self.queue.qsize(),
            'workers_running': len(self.workers) if self.is_running else 0
        }

