import time
import os
import base64
import statistics
import json
import secrets
from typing import Dict, List
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

@dataclass
class BenchmarkData:
    name: str
    size: int
    content: bytes

class EnhancedEncryptionBenchmark:
    def __init__(self):
        # Initialize keys and ciphers
        self._initialize_algorithms()
        self._generate_test_data()

    def _initialize_algorithms(self):
        # Fernet
        self.fernet_key = Fernet.generate_key()
        self.fernet = Fernet(self.fernet_key)
        
        # AES
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        self.aes_key = kdf.derive(b"password")
        self.aes_iv = os.urandom(16)
        
        # RSA
        self.rsa_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.rsa_public_key = self.rsa_key.public_key()
        
        # ChaCha20
        self.chacha_key = os.urandom(32)
        self.chacha_nonce = os.urandom(16)

    def _generate_test_data(self):
        self.test_datasets = [
            # Small data (typical for single fields)
            BenchmarkData(
                "email",
                50,
                b"user.name@example.com"
            ),
            # Medium data (JSON records)
            BenchmarkData(
                "user_record",
                500,
                json.dumps({
                    "id": 12345,
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                    "phone": "+1234567890",
                    "address": "123 Street, City, Country",
                    "ssn": "123-45-6789",
                    "dob": "1990-01-01"
                }).encode()
            ),
            # Large data (multiple records)
            BenchmarkData(
                "multiple_records",
                5000,
                json.dumps([{
                    "id": i,
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "data": "x" * 100
                } for i in range(50)]).encode()
            ),
            # Very large data (batch processing)
            BenchmarkData(
                "batch_records",
                50000,
                json.dumps([{
                    "id": i,
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "data": "x" * 1000
                } for i in range(500)]).encode()
            )
        ]

    def test_fernet(self, data: bytes) -> dict:
        # Warm up
        self.fernet.encrypt(b"warmup")
        
        # Test encryption
        start_time = time.perf_counter()
        encrypted = self.fernet.encrypt(data)
        encryption_time = time.perf_counter() - start_time
        
        # Test decryption
        start_time = time.perf_counter()
        decrypted = self.fernet.decrypt(encrypted)
        decryption_time = time.perf_counter() - start_time
        
        return {
            "algorithm": "Fernet",
            "encryption_time": encryption_time,
            "decryption_time": decryption_time,
            "encrypted_size": len(encrypted),
            "original_size": len(data)
        }

    def test_aes(self, data: bytes) -> dict:
        # Create cipher
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(self.aes_iv))
        
        # Add padding
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        
        # Test encryption
        start_time = time.perf_counter()
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        encryption_time = time.perf_counter() - start_time
        
        # Test decryption
        start_time = time.perf_counter()
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(encrypted) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        decryption_time = time.perf_counter() - start_time
        
        return {
            "algorithm": "AES-256-CBC",
            "encryption_time": encryption_time,
            "decryption_time": decryption_time,
            "encrypted_size": len(encrypted),
            "original_size": len(data)
        }

    def test_chacha20(self, data: bytes) -> dict:
        # Create cipher
        algorithm = algorithms.ChaCha20(self.chacha_key, self.chacha_nonce)
        cipher = Cipher(algorithm, mode=None)
        
        # Test encryption
        start_time = time.perf_counter()
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(data)
        encryption_time = time.perf_counter() - start_time
        
        # Test decryption
        start_time = time.perf_counter()
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted)
        decryption_time = time.perf_counter() - start_time
        
        return {
            "algorithm": "ChaCha20",
            "encryption_time": encryption_time,
            "decryption_time": decryption_time,
            "encrypted_size": len(encrypted),
            "original_size": len(data)
        }

    def test_rsa(self, data: bytes) -> dict:
        # Test encryption
        start_time = time.perf_counter()
        encrypted = self.rsa_public_key.encrypt(
            data,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        encryption_time = time.perf_counter() - start_time
        
        # Test decryption
        start_time = time.perf_counter()
        decrypted = self.rsa_key.decrypt(
            encrypted,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        decryption_time = time.perf_counter() - start_time
        
        return {
            "algorithm": "RSA-2048",
            "encryption_time": encryption_time,
            "decryption_time": decryption_time,
            "encrypted_size": len(encrypted),
            "original_size": len(data)
        }

    def run_benchmark(self, iterations: int = 100):
        results = []
        
        for dataset in self.test_datasets:
            print(f"\nBenchmarking dataset: {dataset.name} ({dataset.size} bytes)")
            
            dataset_results = {
                "dataset_name": dataset.name,
                "dataset_size": dataset.size,
                "algorithms": {
                    "fernet": [],
                    "aes": [],
                    "chacha20": [],
                }
            }
            
            # Don't test RSA for large datasets (due to size limitations)
            if dataset.size < 190:  # RSA-2048 limitation
                dataset_results["algorithms"]["rsa"] = []
            
            for _ in range(iterations):
                # Test each algorithm
                dataset_results["algorithms"]["fernet"].append(
                    self.test_fernet(dataset.content))
                dataset_results["algorithms"]["aes"].append(
                    self.test_aes(dataset.content))
                dataset_results["algorithms"]["chacha20"].append(
                    self.test_chacha20(dataset.content))
                
                if dataset.size < 190:
                    dataset_results["algorithms"]["rsa"].append(
                        self.test_rsa(dataset.content))
            
            results.append(dataset_results)
        
        return self.analyze_results(results)

    def analyze_results(self, results: List[Dict]) -> Dict:
        analyzed = {}
        
        for dataset_result in results:
            dataset_name = dataset_result["dataset_name"]
            analyzed[dataset_name] = {
                "size": dataset_result["dataset_size"],
                "algorithms": {}
            }
            
            for algo_name, algo_results in dataset_result["algorithms"].items():
                if not algo_results:  # Skip if no results (e.g., RSA for large data)
                    continue
                    
                encryption_times = [r["encryption_time"] for r in algo_results]
                decryption_times = [r["decryption_time"] for r in algo_results]
                
                analyzed[dataset_name]["algorithms"][algo_name] = {
                    "avg_encryption_time": statistics.mean(encryption_times),
                    "avg_decryption_time": statistics.mean(decryption_times),
                    "min_encryption_time": min(encryption_times),
                    "max_encryption_time": max(encryption_times),
                    "encryption_stddev": statistics.stdev(encryption_times),
                    "size_overhead": algo_results[0]["encrypted_size"] - 
                                   algo_results[0]["original_size"]
                }
        
        return analyzed

def print_results(results: Dict):
    print("\nDetailed Benchmark Results:")
    print("=" * 80)
    
    for dataset_name, dataset_data in results.items():
        print(f"\nDataset: {dataset_name}")
        print(f"Original Size: {dataset_data['size']} bytes")
        print("-" * 80)
        
        # Sort algorithms by average encryption time
        sorted_algos = sorted(
            dataset_data["algorithms"].items(),
            key=lambda x: x[1]["avg_encryption_time"]
        )
        
        for algo_name, stats in sorted_algos:
            print(f"\n{algo_name.upper()}:")
            print(f"  Encryption Time: {stats['avg_encryption_time']*1000:.3f} ms")
            print(f"  Decryption Time: {stats['avg_decryption_time']*1000:.3f} ms")
            print(f"  Size Overhead: {stats['size_overhead']} bytes")
            print(f"  Min Encryption Time: {stats['min_encryption_time']*1000:.3f} ms")
            print(f"  Max Encryption Time: {stats['max_encryption_time']*1000:.3f} ms")
            print(f"  Std Dev: {stats['encryption_stddev']*1000:.3f} ms")

if __name__ == "__main__":
    benchmark = EnhancedEncryptionBenchmark()
    results = benchmark.run_benchmark(iterations=100)
    print_results(results)
