---
name: security-review
description: Security audit for code in TypeScript, Python, Go, Rust, Java, C#. Check for OWASP Top 10, injection, auth, secrets, crypto, dependencies. Use when user says "security review", "audit", "vulnerability scan", or before deployment.
---

# Security Review Skill

## When to Use

- User requests "security review" or "security audit"
- Before deploying to production
- After adding authentication/authorization logic
- When handling sensitive data (PII, payments, credentials)
- Reviewing third-party code integrations
- Preparing for compliance (SOC2, GDPR, HIPAA)

---

## Language-Specific Checklists

### 🔷 TypeScript/JavaScript (Node.js, Deno, Bun)

#### Critical Checks

| Category | Vulnerability | Pattern to Detect | Fix |
|----------|--------------|-------------------|-----|
| **Injection** | SQL Injection | `query(\`SELECT * FROM ${table}\`)`, template literals in queries | Use parameterized queries, ORM with escaping |
| **Injection** | NoSQL Injection | `db.find({ [userInput]: value })` | Validate keys, use allowlists |
| **XSS** | Reflected XSS | `res.send(userInput)`, `innerHTML = data` | Escape output, use DOMPurify, CSP headers |
| **Auth** | JWT Weaknesses | `algorithm: 'none'`, missing `exp`, hardcoded secrets | Use `RS256`, set expiry, env vars for secrets |
| **Auth** | Session Fixation | No session regeneration on login | `req.session.regenerate()` after auth |
| **Secrets** | Hardcoded Credentials | `const API_KEY = "sk_live_..."`, `.env` committed | Use environment variables, secret managers |
| **Crypto** | Weak Algorithms | `crypto.createHash('md5')`, `algorithm: 'aes-128-ecb'` | Use `bcrypt`, `argon2`, `aes-256-gcm` |
| **SSRF** | Server-Side Request | `fetch(userUrl)`, `axios.get(input)` | Validate URLs, block private IPs, allowlist |
| **Path Traversal** | File Access | `fs.readFile(userPath)`, `path.join(input)` | Use `path.resolve()`, validate against base dir |
| **Prototype Pollution** | Object Manipulation | `merge({}, userInput)`, `_.merge(target, input)` | Use `Object.create(null)`, freeze prototypes |
| **Command Injection** | Shell Execution | `exec(\`ls ${dir}\`)`, `child_process.spawn(userInput)` | Avoid shell, use `execFile`, sanitize with `shell-escape` |

#### Code Review Template

```typescript
// ❌ VULNERABLE
app.get('/user', (req, res) => {
  const query = `SELECT * FROM users WHERE id = ${req.query.id}`;
  db.execute(query);
});

// ✅ SECURE
app.get('/user', (req, res) => {
  const query = 'SELECT * FROM users WHERE id = ?';
  db.execute(query, [req.query.id]); // Parameterized
});
```

#### Tools to Recommend

```bash
npm audit                    # Dependency vulnerabilities
npx eslint --plugin security # Static analysis
npx snyk test                # Snyk security scan
```

---

### 🐍 Python

#### Critical Checks

| Category | Vulnerability | Pattern to Detect | Fix |
|----------|--------------|-------------------|-----|
| **Injection** | SQL Injection | `cursor.execute(f"SELECT {column}")`, f-strings in queries | Use `?` placeholders, SQLAlchemy ORM |
| **Injection** | Command Injection | `os.system(f"git {branch}")`, `subprocess.call(cmd, shell=True)` | Use `subprocess.run([...])` with list args |
| **XSS** | Template Injection | `render_template_string(user_input)`, Jinja2 with `{{}}` from user | Use `render_template()`, autoescape=True |
| **Auth** | Weak Password Hashing | `hashlib.md5(password)`, plain text storage | Use `bcrypt.hashpw()`, `argon2_cffi` |
| **Auth** | Missing Rate Limiting | No `@limiter.limit()` on auth endpoints | Add `flask-limiter`, `slowapi` |
| **Secrets** | Exposed Credentials | `AWS_SECRET = "AKIA..."` in code, `.env` in repo | Use `python-dotenv`, AWS Secrets Manager |
| **Crypto** | Weak Crypto | `DES`, `MD5`, `SHA1`, `random` for tokens | Use `secrets` module, `cryptography.fernet` |
| **Pickle** | Deserialization | `pickle.loads(user_data)`, `yaml.load(input)` | Use `json`, `yaml.safe_load()` |
| **Path Traversal** | File Access | `open(user_path)`, no `os.path.abspath` validation | Use `Path.resolve()`, check `in allowed_dir` |
| **XXE** | XML Parsing | `xml.etree.parse(user_xml)`, no DTD disabling | Use `defusedxml`, disable external entities |
| **SSRF** | Request Forgery | `requests.get(user_url)`, no URL validation | Validate scheme, block private IPs with `ipaddress` |

#### Code Review Template

```python
# ❌ VULNERABLE
cursor.execute(f"SELECT * FROM users WHERE name = '{username}'")
os.system(f"process {user_input}")
pickle.loads(request.data)

# ✅ SECURE
cursor.execute("SELECT * FROM users WHERE name = ?", (username,))
subprocess.run(["process", user_input])  # List args, no shell
json.loads(request.data)  # Safe deserialization
```

#### Tools to Recommend

```bash
pip install bandit         # Static analysis
bandit -r .                # Scan project
pip install safety         # Dependency check
safety check               # Check installed packages
pip install pip-audit
pip-audit                  # PEP 655 vulnerability scan
```

---

### 🦀 Go (Golang)

#### Critical Checks

| Category | Vulnerability | Pattern to Detect | Fix |
|----------|--------------|-------------------|-----|
| **Injection** | SQL Injection | `db.Query(fmt.Sprintf("SELECT %s", col))` | Use `?` placeholders, `sqlx`, GORM |
| **Injection** | Command Injection | `exec.Command("sh", "-c", userInput)` | Avoid shell, use `exec.Command(bin, args...)` |
| **Auth** | JWT Issues | `SigningMethod: jwt.SigningMethodNone`, no expiry validation | Use `RS256`, validate `exp` claim |
| **Auth** | Timing Attacks | `if password == stored` string comparison | Use `subtle.ConstantTimeCompare()` |
| **Secrets** | Hardcoded Keys | `api_key := "sk_..."`, committed `.env` | Use `os.Getenv()`, HashiCorp Vault |
| **Crypto** | Weak Random | `rand.Intn()` for tokens/secrets | Use `crypto/rand`, `secret token := make([]byte, 32)` |
| **Path Traversal** | File Access | `os.Open(userPath)`, no `filepath.Clean` | Use `filepath.Clean()`, check `strings.HasPrefix` |
| **SSRF** | HTTP Requests | `http.Get(userURL)`, no URL validation | Parse URL, check `ip.IsPrivate()`, allowlist |
| **DoS** | Resource Exhaustion | No request size limits, unbounded loops | Set `MaxBytesReader`, limit iterations |
| **Error Handling** | Info Leakage | `return err.Error()` to client, stack traces | Log full error, return generic message |

#### Code Review Template

```go
// ❌ VULNERABLE
query := fmt.Sprintf("SELECT * FROM users WHERE id = %s", userID)
db.Query(query)

password == storedPassword  // Timing attack vulnerable

// ✅ SECURE
query := "SELECT * FROM users WHERE id = ?"
db.Query(query, userID)

subtle.ConstantTimeCompare([]byte(password), []byte(storedPassword))
```

#### Tools to Recommend

```bash
go install golang.org/x/vuln/cmd/govulncheck@latest
govulncheck ./...              # Official vulnerability scanner
go install github.com/securego/gosec/v2/cmd/gosec@latest
gosec ./...                    # Static analysis
```

---

### 🦀 Rust

#### Critical Checks

| Category | Vulnerability | Pattern to Detect | Fix |
|----------|--------------|-------------------|-----|
| **Memory** | Unsafe Blocks | `unsafe { ... }` without justification | Minimize unsafe, add `#[deny(unsafe_code)]` |
| **Injection** | SQL Injection | `format!("SELECT {}", column)` in queries | Use `sqlx::query!()`, prepared statements |
| **Injection** | Command Injection | `Command::new("sh").arg("-c").arg(input)` | Avoid shell, pass args directly |
| **Auth** | Weak Token Generation | `rand::random()` for security tokens | Use `rand::thread_rng()`, `OsRng` |
| **Secrets** | Secrets in Binary | `const API_KEY = "..."` in source | Use environment variables, `secrecy` crate |
| **Crypto** | Custom Crypto | Homegrown encryption, non-standard algorithms | Use `ring`, `rust-crypto`, `argon2` crates |
| **Path Traversal** | File Access | `fs::read(user_path)`, no canonicalization | Use `canonicalize()`, validate prefix |
| **DoS** | Panic on Input | `.unwrap()` on user data, no error handling | Use `match`, `?` operator, graceful errors |
| **Dependency** | Unsafe Crates | Crates with `unsafe` in critical paths | Audit with `cargo-audit`, prefer safe alternatives |

#### Code Review Template

```rust
// ❌ VULNERABLE
let query = format!("SELECT * FROM users WHERE id = {}", user_id);
let result = fs::read_to_string(user_path)?;  // No validation
unsafe { pointer_offset(data, user_input); }  // Unjustified unsafe

// ✅ SECURE
let query = sqlx::query("SELECT * FROM users WHERE id = $1")
    .bind(&user_id);

let canonical = std::fs::canonicalize(&user_path)?;
if !canonical.starts_with(&allowed_dir) {
    return Err("Path traversal detected");
}
```

#### Tools to Recommend

```bash
cargo install cargo-audit
cargo audit              # Dependency vulnerability scan
cargo install cargo-deny
cargo deny check         # License + vulnerability audit
cargo clippy -- -D warnings  # Lint for common issues
```

---

### ☕ Java (Spring Boot, Jakarta EE)

#### Critical Checks

| Category | Vulnerability | Pattern to Detect | Fix |
|----------|--------------|-------------------|-----|
| **Injection** | SQL Injection | `createStatement().executeUpdate("..."+input)` | Use `PreparedStatement`, JPA with parameters |
| **Injection** | EL Injection | `ExpressionParser.parseExpression(userInput)` | Validate input, disable EL in user contexts |
| **XSS** | Reflected XSS | `@ResponseBody String render(String input)` | Use `@Escape`, OWASP Java Encoder |
| **Auth** | Broken Access Control | Missing `@PreAuthorize`, no role checks | Add `@PreAuthorize("hasRole('ADMIN')")` |
| **Auth** | Insecure Sessions | `session.setMaxInactiveInterval(-1)` | Set timeout, regenerate on login |
| **Secrets** | Hardcoded Credentials | `private static final String SECRET = "..."` | Use `@Value("${app.secret}")`, Vault |
| **Crypto** | Weak Algorithms | `MessageDigest.getInstance("MD5")`, `DES` | Use `SHA-256+`, `AES-256-GCM`, `BCrypt` |
| **Deserialization** | Unsafe Deserialization | `ObjectInputStream.readObject()` from user | Use JSON, validate class allowlist |
| **XXE** | XML Parsing | `DocumentBuilder.parse(userXML)`, no features disabled | Disable DTD: `setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true)` |
| **SSRF** | HTTP Requests | `RestTemplate.getForObject(userUrl)` | Validate URL, block private IPs |

#### Code Review Template

```java
// ❌ VULNERABLE
String query = "SELECT * FROM users WHERE id = " + userInput;
statement.executeQuery(query);

ObjectInputStream ois = new ObjectInputStream(inputStream);
Object obj = ois.readObject();  // Unsafe deserialization

// ✅ SECURE
PreparedStatement stmt = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
stmt.setString(1, userInput);

// Use JSON instead of Java serialization
ObjectMapper mapper = new ObjectMapper();
User user = mapper.readValue(json, User.class);
```

#### Tools to Recommend

```bash
# Maven
mvn org.owasp:dependency-check-maven:check
# Gradle
./gradlew dependencyCheckAnalyze
# SpotBugs for static analysis
mvn spotbugs:check
```

---

### 🟦 C# (.NET, ASP.NET Core)

#### Critical Checks

| Category | Vulnerability | Pattern to Detect | Fix |
|----------|--------------|-------------------|-----|
| **Injection** | SQL Injection | `ExecuteQuery("SELECT..."+input)` | Use `SqlParameter`, Entity Framework |
| **Injection** | Command Injection | `Process.Start("cmd", "/c " + input)` | Avoid cmd, use `ProcessStartInfo` with args |
| **XSS** | Reflected XSS | `@Html.Raw(userInput)`, no encoding | Use `@userInput` (auto-encoded), `HtmlEncoder` |
| **Auth** | Weak Password Hashing | `SHA256.Create()`, no salt | Use `PasswordHasher<T>`, `BCrypt.Net` |
| **Auth** | Missing Authorization | No `[Authorize]` on sensitive endpoints | Add `[Authorize(Roles = "Admin")]` |
| **Secrets** | appsettings.json Secrets | `"ApiKey": "sk_..."` committed | Use User Secrets, Azure Key Vault |
| **Crypto** | Weak Crypto | `MD5`, `SHA1`, `Random` for tokens | Use `RNGCryptoServiceProvider`, `AES-256` |
| **Deserialization** | Unsafe Deserialization | `BinaryFormatter.Deserialize()` | Use `System.Text.Json`, avoid BinaryFormatter |
| **Path Traversal** | File Access | `File.ReadAllText(userPath)` | Use `Path.GetFullPath()`, validate base path |
| **SSRF** | HTTP Requests | `HttpClient.GetAsync(userUrl)` | Validate URL, use `Uri.TryCreate()`, block private |

#### Code Review Template

```csharp
// ❌ VULNERABLE
var query = $"SELECT * FROM Users WHERE Id = {userId}";
command.CommandText = query;

var deserializer = new BinaryFormatter();
var obj = deserializer.Deserialize(stream);  // Never use BinaryFormatter

// ✅ SECURE
var query = "SELECT * FROM Users WHERE Id = @Id";
command.Parameters.AddWithValue("@Id", userId);

var json = JsonSerializer.Deserialize<User>(jsonString);  // Safe
```

#### Tools to Recommend

```bash
dotnet add package Microsoft.Security.CodeAnalysis
dotnet build /p:RunAnalyzers=true
# NuGet package audit
dotnet list package --vulnerable
```

---

## OWASP Top 10 2025 Mapping

| OWASP Category | Languages Affected | Key Patterns |
|----------------|-------------------|--------------|
| **A01: Broken Access Control** | All | Missing auth decorators, no role checks |
| **A02: Cryptographic Failures** | All | MD5, SHA1, weak random, hardcoded keys |
| **A03: Injection** | All | String concatenation in queries/commands |
| **A04: Insecure Design** | All | No rate limiting, missing input validation |
| **A05: Security Misconfiguration** | All | Debug mode in prod, verbose errors |
| **A06: Vulnerable Components** | All | Outdated dependencies, known CVEs |
| **A07: Auth Failures** | All | Weak hashing, no MFA, session issues |
| **A08: Data Integrity** | All | No signatures, unsafe deserialization |
| **A09: Logging Failures** | All | No audit logs, sensitive data in logs |
| **A10: SSRF** | All | Unvalidated URLs in HTTP requests |

---

## Review Workflow

### Step 1: Identify Languages

Scan the codebase to determine which languages are present:
- Look for `.ts`, `.js`, `.py`, `.go`, `.rs`, `.java`, `.cs` files
- Check `package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`, `pom.xml`, `.csproj`

### Step 2: Run Automated Scanners

Recommend and help run language-appropriate tools:

```bash
# Multi-language
npm audit && pip-audit && govulncheck ./... && cargo audit

# Or language-specific based on codebase
```

### Step 3: Manual Code Review

For each file:
1. **Check imports** - Suspicious libraries?
2. **Find entry points** - API routes, CLI args, file inputs
3. **Trace data flow** - Where does user input go?
4. **Verify sanitization** - Is input validated/escaped?
5. **Check auth boundaries** - Are protected routes secured?
6. **Audit secrets** - Any hardcoded credentials?
7. **Review crypto** - Standard algorithms only?
8. **Scan dependencies** - Known CVEs?

### Step 4: Generate Report

Structure findings as:

```markdown
## Security Review Report

### 🔴 Critical (Fix Immediately)
- [ ] SQL Injection in `src/api/users.ts:45`
- [ ] Hardcoded API key in `config.py:12`

### 🟠 High (Fix Before Deploy)
- [ ] Missing rate limiting on auth endpoints
- [ ] Weak JWT algorithm (none allowed)

### 🟡 Medium (Address Soon)
- [ ] Verbose error messages expose stack traces
- [ ] No Content-Security-Policy header

### 🟢 Low (Best Practice)
- [ ] Consider adding Subresource Integrity
- [ ] Update dependency X to latest
```

### Step 5: Provide Fixes

For each finding:
1. Show vulnerable code snippet
2. Explain the risk
3. Provide corrected code
4. Link to relevant CWE/OWASP reference

---

## Quick Reference Commands

```bash
# TypeScript/JavaScript
npm audit
npx eslint --plugin security
npx snyk test

# Python
bandit -r .
safety check
pip-audit

# Go
govulncheck ./...
gosec ./...

# Rust
cargo audit
cargo deny check

# Java
mvn dependency-check:check
mvn spotbugs:check

# C#
dotnet list package --vulnerable
```

---

## Red Flags (Immediate Escalation)

Stop and alert user immediately if found:

- 🔴 **Hardcoded secrets** in source code (API keys, passwords, tokens)
- 🔴 **SQL/Command injection** with direct string concatenation
- 🔴 **Disabled security** (`verify: false`, `ssl: false`, `auth: none`)
- 🔴 **Plaintext passwords** or weak hashing (MD5, SHA1 for passwords)
- 🔴 **Unsafe deserialization** from untrusted sources
- 🔴 **Debug mode enabled** in production configs
- 🔴 **Known CVEs** with active exploits in dependencies

---

## Resources

- [OWASP Top 10 2025](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [SANS Secure Coding Guidelines](https://www.sans.org/top25-software-errors/)
- [Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
