# Security Review Examples

## Example 1: SQL Injection (TypeScript)

### ❌ Vulnerable Code
```typescript
// src/api/users.ts
@app.get('/user/:id')
async getUser(req: Request, res: Response) {
  const userId = req.params.id;
  const query = `SELECT * FROM users WHERE id = ${userId}`;
  const result = await db.query(query);
  return res.json(result);
}
```

### ✅ Secure Code
```typescript
// src/api/users.ts
@app.get('/user/:id')
async getUser(req: Request, res: Response) {
  const userId = req.params.id;
  
  // Validate input
  if (!/^\d+$/.test(userId)) {
    return res.status(400).json({ error: 'Invalid user ID' });
  }
  
  // Parameterized query
  const result = await db.query(
    'SELECT id, name, email FROM users WHERE id = ?',
    [userId]
  );
  
  return res.json(result);
}
```

**Risk**: Attacker can extract entire database with `' OR '1'='1`
**CWE**: CWE-89 (SQL Injection)
**OWASP**: A03:2025 - Injection

---

## Example 2: Hardcoded Secrets (Python)

### ❌ Vulnerable Code
```python
# config.py
DATABASE_URL = "postgresql://admin:SuperSecret123@prod-db.internal:5432/main"
API_KEY = "sk_live_51HxY2fDKjP9xMnQ8zR7vW3pL"
AWS_SECRET = "AKIAIOSFODNN7EXAMPLE+wJalrXUtnFEMI"
```

### ✅ Secure Code
```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file (not committed to git)

DATABASE_URL = os.environ.get("DATABASE_URL")
API_KEY = os.environ.get("API_KEY")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

# Validate required secrets exist
if not all([DATABASE_URL, API_KEY, AWS_SECRET_ACCESS_KEY]):
    raise ValueError("Missing required environment variables")
```

```bash
# .env (add to .gitignore)
DATABASE_URL=postgresql://user:pass@localhost:5432/main
API_KEY=your_dev_key_here
AWS_SECRET_ACCESS_KEY=your_dev_secret
```

```
# .gitignore
.env
*.env
!.env.example
```

**Risk**: Credentials exposed in source control, accessible to anyone with repo access
**CWE**: CWE-522 (Insufficiently Protected Credentials)
**OWASP**: A07:2025 - Identification and Authentication Failures

---

## Example 3: XSS (JavaScript/React)

### ❌ Vulnerable Code
```jsx
// src/components/Comment.jsx
function Comment({ userContent }) {
  return (
    <div className="comment">
      <div dangerouslySetInnerHTML={{ __html: userContent }} />
    </div>
  );
}
```

### ✅ Secure Code
```jsx
// src/components/Comment.jsx
import DOMPurify from 'dompurify';

function Comment({ userContent }) {
  // Option 1: Let React auto-escape (preferred for plain text)
  return (
    <div className="comment">
      {userContent}
    </div>
  );
  
  // Option 2: If HTML is required, sanitize first
  // const sanitized = DOMPurify.sanitize(userContent, {
  //   ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a'],
  //   ALLOWED_ATTR: ['href']
  // });
  // return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
}
```

**Risk**: Attacker injects `<script>` to steal session cookies
**CWE**: CWE-79 (XSS)
**OWASP**: A03:2025 - Injection

---

## Example 4: Weak Password Hashing (Python)

### ❌ Vulnerable Code
```python
# auth.py
import hashlib

def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()

def verify_password(password: str, stored: str) -> bool:
    return hash_password(password) == stored
```

### ✅ Secure Code
```python
# auth.py
import bcrypt
from argon2 import PasswordHasher

# Option 1: bcrypt
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, stored: str) -> bool:
    return bcrypt.checkpw(password.encode(), stored.encode())

# Option 2: Argon2 (recommended)
ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, stored: str) -> bool:
    try:
        ph.verify(stored, password)
        return True
    except:
        return False
```

**Risk**: MD5 can be brute-forced in seconds; rainbow tables widely available
**CWE**: CWE-328 (Weak Hash)
**OWASP**: A02:2025 - Cryptographic Failures

---

## Example 5: JWT Security (Go)

### ❌ Vulnerable Code
```go
// auth/jwt.go
func GenerateToken(userID string) (string, error) {
    token := jwt.New(jwt.SigningMethodNone)  // ❌ No signature!
    claims := token.Claims.(jwt.MapClaims)
    claims["user_id"] = userID
    // ❌ No expiration
    return token.SignedString([]byte(""))
}
```

### ✅ Secure Code
```go
// auth/jwt.go
import (
    "time"
    "github.com/golang-jwt/jwt/v5"
)

var jwtKey = []byte(os.Getenv("JWT_SECRET"))  // From env var

func GenerateToken(userID string) (string, error) {
    expirationTime := time.Now().Add(15 * time.Minute)
    
    claims := &jwt.MapClaims{
        "user_id": userID,
        "exp":     expirationTime.Unix(),
        "iat":     time.Now().Unix(),
    }
    
    token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
    return token.SignedString(jwtKey)
}

func ValidateToken(tokenString string) (*jwt.MapClaims, error) {
    token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
        // Validate algorithm
        if _, ok := token.Method.(*jwt.SigningMethodRSA); !ok {
            return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
        }
        return jwtKey, nil
    })
    
    if err != nil || !token.Valid {
        return nil, fmt.Errorf("invalid token")
    }
    
    claims, ok := token.Claims.(*jwt.MapClaims)
    if !ok {
        return nil, fmt.Errorf("invalid claims")
    }
    
    return claims, nil
}
```

**Risk**: `SigningMethodNone` allows forging any token without secret
**CWE**: CWE-347 (Improper Verification of Cryptographic Signature)
**OWASP**: A07:2025 - Identification and Authentication Failures

---

## Example 6: Path Traversal (Rust)

### ❌ Vulnerable Code
```rust
// src/file_handler.rs
use std::fs;

fn read_file(user_path: &str) -> Result<String, io::Error> {
    fs::read_to_string(user_path)  // ❌ No validation
}
```

### ✅ Secure Code
```rust
// src/file_handler.rs
use std::fs;
use std::path::{Path, PathBuf};

fn read_file(user_path: &str, base_dir: &Path) -> Result<String, io::Error> {
    // Canonicalize the base directory
    let canonical_base = base_dir.canonicalize()?;
    
    // Join and canonicalize user path
    let requested_path = canonical_base.join(user_path);
    let canonical_path = requested_path.canonicalize()?;
    
    // Verify path is within base directory
    if !canonical_path.starts_with(&canonical_base) {
        return Err(io::Error::new(
            io::ErrorKind::PermissionDenied,
            "Path traversal detected"
        ));
    }
    
    fs::read_to_string(&canonical_path)
}
```

**Risk**: Attacker accesses `/etc/passwd` with `../../../etc/passwd`
**CWE**: CWE-22 (Path Traversal)
**OWASP**: A01:2025 - Broken Access Control

---

## Example 7: Unsafe Deserialization (Java)

### ❌ Vulnerable Code
```java
// src/main/java/com/example/DataLoader.java
import java.io.*;

public class DataLoader {
    public Object loadData(InputStream input) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(input);
        return ois.readObject();  // ❌ Unsafe deserialization
    }
}
```

### ✅ Secure Code
```java
// src/main/java/com/example/DataLoader.java
import com.fasterxml.jackson.databind.ObjectMapper;

public class DataLoader {
    private final ObjectMapper mapper = new ObjectMapper();
    
    public <T> T loadData(InputStream input, Class<T> clazz) throws Exception {
        // Use JSON instead of Java serialization
        return mapper.readValue(input, clazz);
    }
    
    // If ObjectInputStream is absolutely required:
    public Object loadSafeData(InputStream input) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(input) {
            @Override
            protected Class<?> resolveClass(ObjectStreamClass desc) throws IOException {
                // Allowlist of safe classes
                List<String> allowed = List.of(
                    "com.example.SafeData",
                    "java.lang.String",
                    "java.util.ArrayList"
                );
                if (!allowed.contains(desc.getName())) {
                    throw new IOException("Unauthorized class: " + desc.getName());
                }
                return super.resolveClass(desc);
            }
        };
        return ois.readObject();
    }
}
```

**Risk**: Remote code execution via crafted serialized objects (ysoserial)
**CWE**: CWE-502 (Deserialization of Untrusted Data)
**OWASP**: A08:2025 - Software and Data Integrity Failures

---

## Example 8: SSRF (Python)

### ❌ Vulnerable Code
```python
# src/webhook.py
import requests

def fetch_webhook(url: str) -> str:
    response = requests.get(url)  # ❌ No URL validation
    return response.text
```

### ✅ Secure Code
```python
# src/webhook.py
import requests
import socket
import ipaddress
from urllib.parse import urlparse
from ipaddress import ip_address

def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    
    # Only allow HTTP/HTTPS
    if parsed.scheme not in ['http', 'https']:
        return False
    
    # Resolve hostname
    try:
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # Check all resolved IPs
        for addr in socket.getaddrinfo(hostname, None):
            ip = addr[4][0]
            try:
                ip_obj = ip_address(ip)
                # Block private/reserved IPs
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                    return False
            except ValueError:
                continue
    except socket.gaierror:
        return False
    
    return True

def fetch_webhook(url: str) -> str:
    if not is_safe_url(url):
        raise ValueError(f"Unsafe URL: {url}")
    
    response = requests.get(url, timeout=10, allow_redirects=False)
    response.raise_for_status()
    return response.text
```

**Risk**: Attacker accesses internal services (metadata endpoints, admin panels)
**CWE**: CWE-918 (SSRF)
**OWASP**: A10:2025 - SSRF

---

## Example 9: Command Injection (C#)

### ❌ Vulnerable Code
```csharp
// Controllers/FileController.cs
[HttpPost("process")]
public IActionResult ProcessFile(string fileName)
{
    // ❌ Shell injection via fileName
    var process = Process.Start("cmd", $"/c process {fileName}");
    process.WaitForExit();
    return Ok();
}
```

### ✅ Secure Code
```csharp
// Controllers/FileController.cs
[HttpPost("process")]
public IActionResult ProcessFile(string fileName)
{
    // Validate input
    if (!Regex.IsMatch(fileName, @"^[a-zA-Z0-9_-]+\.txt$"))
    {
        return BadRequest("Invalid file name");
    }
    
    // Use ProcessStartInfo without shell
    var startInfo = new ProcessStartInfo
    {
        FileName = "/usr/bin/process",  // Full path
        ArgumentList = { fileName },     // Arguments as list
        RedirectStandardOutput = true,
        RedirectStandardError = true,
        UseShellExecute = false,         // No shell
        CreateNoWindow = true
    };
    
    using var process = new Process { StartInfo = startInfo };
    process.Start();
    process.WaitForExit();
    
    return Ok();
}
```

**Risk**: Attacker executes arbitrary commands with `; rm -rf /`
**CWE**: CWE-78 (OS Command Injection)
**OWASP**: A03:2025 - Injection

---

## Example 10: Missing Rate Limiting (TypeScript/Express)

### ❌ Vulnerable Code
```typescript
// src/routes/auth.ts
@app.post('/login')
async login(req: Request, res: Response) {
  const { email, password } = req.body;
  const user = await validateUser(email, password);
  // ❌ No rate limiting - brute force possible
  return res.json({ token: generateToken(user) });
}
```

### ✅ Secure Code
```typescript
// src/routes/auth.ts
import rateLimit from 'express-rate-limit';
import RedisStore from 'rate-limit-redis';

const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,  // 15 minutes
  max: 5,                     // 5 attempts per window
  store: new RedisStore({
    client: redisClient,
    prefix: 'ratelimit:login:'
  }),
  keyGenerator: (req) => req.body.email || req.ip,
  message: { error: 'Too many login attempts. Try again in 15 minutes.' },
  standardHeaders: true,
  legacyHeaders: false,
});

@app.post('/login')
@loginLimiter  // Apply rate limiting
async login(req: Request, res: Response) {
  const { email, password } = req.body;
  
  // Constant-time response (prevent user enumeration)
  const user = await validateUser(email, password);
  if (!user) {
    await bcrypt.hash(password, 10);  // Waste time
    return res.status(401).json({ error: 'Invalid credentials' });
  }
  
  return res.json({ token: generateToken(user) });
}
```

**Risk**: Attacker brute-forces passwords at high speed
**CWE**: CWE-307 (Improper Restriction of Authentication Attempts)
**OWASP**: A07:2025 - Identification and Authentication Failures

---

## Testing Your Fixes

After applying fixes, verify with:

```bash
# Run security scanners
npm audit && bandit -r . && govulncheck ./...

# Test injection points
sqlmap -u "http://localhost:3000/user?id=1" --batch
xsstrike -u "http://localhost:3000/search?q=test"

# Verify secrets aren't exposed
gitleaks detect --source . -v

# Check headers
curl -I http://localhost:3000 | grep -E "Strict|Content-Security|X-"
```
