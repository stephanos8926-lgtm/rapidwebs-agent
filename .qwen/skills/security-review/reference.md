# Security Review Reference

## CWE Mappings

| CWE ID | Name | Languages | Severity |
|--------|------|-----------|----------|
| CWE-89 | SQL Injection | All | Critical |
| CWE-78 | OS Command Injection | All | Critical |
| CWE-79 | XSS | TS/JS, Java, C# | High |
| CWE-287 | Improper Authentication | All | Critical |
| CWE-522 | Insufficiently Protected Credentials | All | Critical |
| CWE-327 | Broken/Weak Crypto | All | High |
| CWE-330 | Weak Random Numbers | All | High |
| CWE-434 | Unrestricted File Upload | All | High |
| CWE-22 | Path Traversal | All | High |
| CWE-918 | SSRF | All | High |
| CWE-502 | Deserialization of Untrusted Data | Python, Java, C# | Critical |
| CWE-611 | XXE | Python, Java | High |
| CWE-862 | Missing Authorization | All | High |
| CWE-863 | Broken Access Control | All | Critical |

---

## Secure Defaults by Language

### TypeScript/JavaScript
```typescript
// Express security middleware
app.use(helmet());                    // Security headers
app.use(cors({ origin: false }));     // Restrict CORS
app.use(rateLimit({ windowMs: 15 * 60 * 1000, max: 100 }));
app.use(xss());                       // XSS filtering
```

### Python
```python
# Flask security
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
```

### Go
```go
// HTTP server with timeouts
server := &http.Server{
    Addr:         ":8080",
    ReadTimeout:  5 * time.Second,
    WriteTimeout: 10 * time.Second,
    IdleTimeout:  120 * time.Second,
}
```

### Rust
```rust
// Deny unsafe code globally
#![deny(unsafe_code)]
#![forbid(unsafe_code)]
```

### Java (Spring)
```java
// Security config
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws SecurityException {
        http.csrf(csrf -> csrf.disable())  // Only if using JWT
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/**").authenticated()
            );
        return http.build();
    }
}
```

### C# (ASP.NET Core)
```csharp
// Program.cs security
builder.Services.AddControllers()
    .AddJsonOptions(options => {
        options.JsonSerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
    });

// Enable security headers
app.UseHsts();
app.UseHttpsRedirection();
```

---

## Dependency Check Commands

| Language | Command | Tool |
|----------|---------|------|
| npm | `npm audit` | Built-in |
| pip | `pip-audit` | pip-audit |
| pip | `safety check` | safety |
| go | `govulncheck ./...` | govulncheck |
| cargo | `cargo audit` | cargo-audit |
| maven | `mvn dependency-check:check` | OWASP DC |
| gradle | `./gradlew dependencyCheckAnalyze` | OWASP DC |
| dotnet | `dotnet list package --vulnerable` | Built-in |

---

## Secret Detection

Scan for secrets before committing:

```bash
# Using gitleaks
gitleaks detect --source . -v

# Using truffleHog
trufflehog filesystem .

# Using detect-secrets
detect-secrets scan --all-files > .secrets.baseline
```

---

## Security Headers Checklist

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS |
| `Content-Security-Policy` | `default-src 'self'` | Prevent XSS |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS filter |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer |
| `Permissions-Policy` | `geolocation=(), microphone=()` | Restrict features |

---

## Authentication Checklist

- [ ] Passwords hashed with bcrypt/argon2 (NOT MD5, SHA1, SHA256 alone)
- [ ] Minimum password length: 12 characters
- [ ] Rate limiting on login endpoints (max 5 attempts/minute)
- [ ] Account lockout after 10 failed attempts
- [ ] JWT uses RS256 or ES256 (NOT none, HS256)
- [ ] JWT has expiration claim (max 15 minutes for access tokens)
- [ ] Refresh tokens are rotated and have short lifetime
- [ ] Sessions regenerated on login
- [ ] Logout invalidates tokens server-side
- [ ] MFA available for sensitive operations

---

## Input Validation Patterns

### TypeScript
```typescript
import { z } from 'zod';

const UserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(12).max(128),
  age: z.number().min(0).max(150),
});
```

### Python
```python
from pydantic import BaseModel, EmailStr, Field

class User(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    age: int = Field(..., ge=0, le=150)
```

### Go
```go
type User struct {
    Email    string `validate:"required,email"`
    Password string `validate:"required,min=12,max=128"`
    Age      int    `validate:"required,min=0,max=150"`
}
```

---

## Secure Error Handling

### Never expose to users:
- Stack traces
- SQL error messages
- File paths
- Internal IP addresses
- Version numbers

### Always log (server-side):
- Full error details
- Request context
- User ID (if authenticated)
- Timestamp

### Return to users:
- Generic error messages
- Error correlation ID
- HTTP-appropriate status codes
