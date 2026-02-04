# Claude Instructions - Nobodies Profiles (.NET Rewrite)

Project-specific guidance for Claude Code when building the .NET version of this membership management system.

## Project Overview

This is a membership management system for a Spanish nonprofit, rewritten in .NET. Key domains:
- **Identity**: Custom User model (email-based, Google OAuth)
- **Members**: Profile, RoleAssignment, membership status
- **Applications**: Application workflow with state machine
- **Documents**: Legal documents, version tracking, consent management
- **Teams**: Working groups and team memberships
- **GoogleSync**: Google Drive permission provisioning
- **Gdpr**: Data export and anonymization requests

## Recommended Tech Stack

### Core
- **.NET 8** (LTS)
- **ASP.NET Core** - Web framework
- **Entity Framework Core 8** - ORM
- **PostgreSQL** or **SQL Server** - Database
- **Redis** - Caching and message broker

### Key Packages
- `Microsoft.AspNetCore.Identity` - User management, authentication
- `AspNet.Security.OAuth.Google` or `Microsoft.AspNetCore.Authentication.Google` - Google OAuth
- `Stateless` - State machine library (replacement for django-fsm)
- `Hangfire` or `MassTransit` - Background job processing (replacement for Celery)
- `Audit.NET` or custom temporal tables - Audit trails
- `Serilog` - Structured logging

### Project Structure (Clean Architecture)
```
NobodiesProfiles/
├── src/
│   ├── NobodiesProfiles.Domain/           # Entities, enums, domain logic
│   │   ├── Entities/
│   │   │   ├── User.cs
│   │   │   ├── Profile.cs
│   │   │   ├── RoleAssignment.cs
│   │   │   ├── Application.cs
│   │   │   ├── LegalDocument.cs
│   │   │   ├── DocumentVersion.cs
│   │   │   ├── ConsentRecord.cs
│   │   │   ├── ConsentRevocation.cs
│   │   │   ├── Team.cs
│   │   │   └── GoogleResource.cs
│   │   ├── Enums/
│   │   │   ├── ApplicationStatus.cs
│   │   │   ├── MembershipStatus.cs
│   │   │   └── DocumentType.cs
│   │   └── Interfaces/
│   ├── NobodiesProfiles.Application/      # Use cases, DTOs, interfaces
│   │   ├── Features/
│   │   │   ├── Applications/
│   │   │   ├── Members/
│   │   │   ├── Documents/
│   │   │   ├── Teams/
│   │   │   ├── GoogleSync/
│   │   │   └── Gdpr/
│   │   ├── Common/
│   │   └── Interfaces/
│   ├── NobodiesProfiles.Infrastructure/   # EF Core, external services
│   │   ├── Persistence/
│   │   │   ├── ApplicationDbContext.cs
│   │   │   ├── Configurations/            # EF entity configs
│   │   │   └── Migrations/
│   │   ├── Identity/
│   │   ├── Services/
│   │   │   ├── GoogleDriveService.cs
│   │   │   └── BackgroundJobs/
│   │   └── DependencyInjection.cs
│   └── NobodiesProfiles.Web/              # ASP.NET Core web app
│       ├── Controllers/ or Endpoints/
│       ├── Views/ or Pages/
│       ├── wwwroot/
│       ├── Resources/                     # Localization files
│       └── Program.cs
├── tests/
│   ├── NobodiesProfiles.Domain.Tests/
│   ├── NobodiesProfiles.Application.Tests/
│   └── NobodiesProfiles.Integration.Tests/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
└── NobodiesProfiles.sln
```

## Critical Rules

### 1. Custom User Entity
Extend `IdentityUser` with custom properties. All user references should use the custom User type, never the base IdentityUser directly.

```csharp
public class User : IdentityUser<Guid>
{
    public string? DisplayName { get; set; }
    public string PreferredLanguage { get; set; } = "es";
    public DateTime CreatedAt { get; set; }
    public DateTime? LastLoginAt { get; set; }

    public Profile? Profile { get; set; }
}
```

### 2. ConsentRecord Immutability
**NEVER** add update or delete methods to ConsentRecord. This table is append-only for legal compliance. Configure EF Core to prevent modifications.

```csharp
public class ConsentRecord
{
    public Guid Id { get; init; }
    public Guid ProfileId { get; init; }
    public Guid DocumentVersionId { get; init; }
    public DateTime ConsentedAt { get; init; }
    public string IpAddress { get; init; } = null!;
    public string UserAgent { get; init; } = null!;

    // No setters, no update methods
}

// In DbContext configuration:
modelBuilder.Entity<ConsentRecord>()
    .ToTable(tb => tb.HasTrigger("PreventConsentRecordModification")); // Or use EF interceptors
```

### 3. Membership Status is Computed
`Profile.MembershipStatus` is derived from:
- Active RoleAssignment exists?
- All required ConsentRecords for current DocumentVersions?
- Not past re-consent deadline?

Implement as a computed property or database computed column. Never set directly.

```csharp
public class Profile
{
    // ... other properties

    public MembershipStatus MembershipStatus => ComputeMembershipStatus();

    private MembershipStatus ComputeMembershipStatus()
    {
        if (!RoleAssignments.Any(ra => ra.IsActive))
            return MembershipStatus.Inactive;
        if (!HasAllRequiredConsents())
            return MembershipStatus.PendingConsent;
        if (IsReconsentRequired())
            return MembershipStatus.ReconsentRequired;
        return MembershipStatus.Active;
    }
}
```

### 4. Google API Rate Limiting
Always use background jobs for Google API calls. Implement exponential backoff with Polly.

```csharp
// Using Hangfire
[AutomaticRetry(Attempts = 3, DelaysInSeconds = new[] { 60, 120, 240 })]
public async Task ProvisionGoogleAccessAsync(Guid profileId)
{
    // API call with Polly retry policy
}
```

### 5. Spanish is Canonical
For legal documents, Spanish (`es`) content is legally binding. Translations are reference-only. UI must always show Spanish as primary with clear disclaimer on translations.

## Code Patterns

### State Machine (using Stateless)
```csharp
public class Application
{
    public Guid Id { get; set; }
    public ApplicationStatus Status { get; private set; } = ApplicationStatus.Submitted;

    private StateMachine<ApplicationStatus, ApplicationTrigger> _stateMachine;

    public Application()
    {
        ConfigureStateMachine();
    }

    private void ConfigureStateMachine()
    {
        _stateMachine = new StateMachine<ApplicationStatus, ApplicationTrigger>(
            () => Status,
            s => Status = s
        );

        _stateMachine.Configure(ApplicationStatus.Submitted)
            .Permit(ApplicationTrigger.StartReview, ApplicationStatus.UnderReview);

        _stateMachine.Configure(ApplicationStatus.UnderReview)
            .Permit(ApplicationTrigger.Approve, ApplicationStatus.Approved)
            .Permit(ApplicationTrigger.Reject, ApplicationStatus.Rejected)
            .OnEntry(() => OnStartReview());

        _stateMachine.Configure(ApplicationStatus.Approved)
            .OnEntry(() => OnApproved());
    }

    public void StartReview() => _stateMachine.Fire(ApplicationTrigger.StartReview);
    public void Approve() => _stateMachine.Fire(ApplicationTrigger.Approve);

    private void OnApproved()
    {
        // Side effects: create Profile, RoleAssignment via domain events
    }
}
```

### Audit Logging (EF Core Interceptors or Audit.NET)
```csharp
// Option 1: Temporal tables (SQL Server)
modelBuilder.Entity<RoleAssignment>()
    .ToTable("RoleAssignments", tb => tb.IsTemporal());

// Option 2: Shadow properties with interceptor
public class AuditableEntity
{
    public DateTime CreatedAt { get; set; }
    public string CreatedBy { get; set; } = null!;
    public DateTime? ModifiedAt { get; set; }
    public string? ModifiedBy { get; set; }
}
```

### Background Jobs (Hangfire)
```csharp
public interface IGoogleSyncService
{
    Task ProvisionAccessAsync(Guid profileId);
    Task RevokeAccessAsync(Guid profileId);
    Task ReconcileAllAsync();
}

// Scheduled reconciliation
RecurringJob.AddOrUpdate<IGoogleSyncService>(
    "google-reconciliation",
    service => service.ReconcileAllAsync(),
    Cron.Daily);
```

### GDPR Consent UI Pattern
```razor
@* Always show Spanish primary *@
<div class="document-content">
    @Html.Raw(Model.DocumentVersion.SpanishContent)
</div>

@* Translation selector with disclaimer *@
@if (Model.Translations.Any())
{
    <div class="alert alert-warning">
        This translation is for reference only. The Spanish version is legally binding.
    </div>
}

@* Explicit unchecked checkbox *@
<div class="form-check">
    <input type="checkbox" class="form-check-input" id="consent" name="consent" required>
    <label class="form-check-label" for="consent">
        I have read and agree to @Model.Document.Title version @Model.DocumentVersion.VersionNumber.
        I acknowledge that the Spanish version is legally binding.
    </label>
</div>
```

## Testing Approach

### Unit Tests (xUnit + FluentAssertions + NSubstitute)
```csharp
public class ApplicationTests
{
    [Fact]
    public void Approve_WhenUnderReview_ShouldTransitionToApproved()
    {
        var application = new Application();
        application.StartReview();

        application.Approve();

        application.Status.Should().Be(ApplicationStatus.Approved);
    }
}
```

### Integration Tests (TestContainers + WebApplicationFactory)
```csharp
public class ApplicationWorkflowTests : IClassFixture<CustomWebApplicationFactory>
{
    [Fact]
    public async Task FullApplicationFlow_ShouldCreateActiveProfile()
    {
        // Test: Submit → Review → Approve → Sign Documents → Active Member
    }
}
```

### GDPR Tests
- Verify data export includes all personal data
- Verify anonymization replaces PII but preserves structure
- Verify ConsentRecords cannot be modified (throws exception)

## Internationalization

Language is determined by user preference (stored in profile) or a dropdown selector in the UI, not by URL.

```csharp
// Program.cs
builder.Services.AddLocalization(options => options.ResourcesPath = "Resources");
builder.Services.Configure<RequestLocalizationOptions>(options =>
{
    var supportedCultures = new[] { "es", "en", "fr", "de", "pt" };
    options.SetDefaultCulture("es")
        .AddSupportedCultures(supportedCultures)
        .AddSupportedUICultures(supportedCultures);

    // Priority: 1) Cookie (from dropdown), 2) User profile setting, 3) Browser Accept-Language
    options.RequestCultureProviders = new List<IRequestCultureProvider>
    {
        new CookieRequestCultureProvider(),
        new UserProfileCultureProvider(), // Custom provider - see below
        new AcceptLanguageHeaderRequestCultureProvider()
    };
});

// Standard routing without culture segment
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");
```

### Custom Culture Provider (reads from user profile)
```csharp
public class UserProfileCultureProvider : IRequestCultureProvider
{
    public async Task<ProviderCultureResult?> DetermineProviderCultureResult(HttpContext httpContext)
    {
        if (!httpContext.User.Identity?.IsAuthenticated ?? true)
            return null;

        var userService = httpContext.RequestServices.GetRequiredService<IUserService>();
        var userId = httpContext.User.FindFirstValue(ClaimTypes.NameIdentifier);

        if (userId == null)
            return null;

        var preferredLanguage = await userService.GetPreferredLanguageAsync(Guid.Parse(userId));

        return preferredLanguage != null
            ? new ProviderCultureResult(preferredLanguage)
            : null;
    }
}
```

### Language Dropdown Component
```razor
@* _Layout.cshtml - Language selector in corner *@
<div class="language-selector dropdown">
    <button class="btn btn-sm dropdown-toggle" data-bs-toggle="dropdown">
        @CultureInfo.CurrentUICulture.TwoLetterISOLanguageName.ToUpper()
    </button>
    <ul class="dropdown-menu">
        @foreach (var culture in new[] { ("es", "Español"), ("en", "English"), ("fr", "Français"), ("de", "Deutsch"), ("pt", "Português") })
        {
            <li>
                <form asp-action="SetLanguage" asp-controller="Culture" method="post">
                    <input type="hidden" name="culture" value="@culture.Item1" />
                    <button type="submit" class="dropdown-item">@culture.Item2</button>
                </form>
            </li>
        }
    </ul>
</div>
```

### Culture Controller
```csharp
public class CultureController : Controller
{
    private readonly IUserService _userService;

    [HttpPost]
    public async Task<IActionResult> SetLanguage(string culture, string? returnUrl)
    {
        // Set cookie for immediate effect
        Response.Cookies.Append(
            CookieRequestCultureProvider.DefaultCookieName,
            CookieRequestCultureProvider.MakeCookieValue(new RequestCulture(culture)),
            new CookieOptions { Expires = DateTimeOffset.UtcNow.AddYears(1) }
        );

        // Also save to user profile if authenticated
        if (User.Identity?.IsAuthenticated ?? false)
        {
            var userId = Guid.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
            await _userService.UpdatePreferredLanguageAsync(userId, culture);
        }

        return LocalRedirect(returnUrl ?? "/");
    }
}
```

## Docker Deployment

```dockerfile
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
WORKDIR /app
EXPOSE 8080

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY . .
RUN dotnet restore
RUN dotnet publish -c Release -o /app/publish

FROM base AS final
WORKDIR /app
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "NobodiesProfiles.Web.dll"]
```

```yaml
# docker-compose.yml
services:
  web:
    build: .
    environment:
      - ConnectionStrings__DefaultConnection=Host=db;Database=profiles;Username=postgres;Password=secret
      - Redis__ConnectionString=redis:6379
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.profiles.rule=Host(`profiles.nobodies.team`)"
      - "traefik.http.routers.profiles.entrypoints=websecure"
      - "traefik.http.routers.profiles.tls=true"
    depends_on:
      - db
      - redis

  db:
    image: postgres:16

  redis:
    image: redis:7

  hangfire:
    build: .
    command: ["dotnet", "NobodiesProfiles.Web.dll", "--hangfire-server"]
    depends_on:
      - db
      - redis
```

## Entity Summary

| Domain Entity | Purpose |
|---------------|---------|
| `User` | Authentication, extends IdentityUser |
| `Profile` | Member profile, linked to User |
| `RoleAssignment` | Assigns roles to profiles with date ranges |
| `Role` | Defines member roles (e.g., Full Member, Associate) |
| `Application` | Membership application with FSM workflow |
| `LegalDocument` | Document metadata (Privacy Policy, Terms, etc.) |
| `DocumentVersion` | Versioned content, Spanish canonical |
| `ConsentRecord` | Immutable consent log |
| `ConsentRevocation` | Records consent withdrawal |
| `Team` | Working groups |
| `TeamMembership` | Profile-Team relationship |
| `GoogleResource` | Google Drive folders/files to provision |
| `RoleGoogleAccess` | Links Roles to GoogleResources |
| `TeamGoogleAccess` | Links Teams to GoogleResources |
| `GdprRequest` | Data export or anonymization requests |

## Common Tasks

### Adding a New Legal Document Type
1. Add value to `DocumentType` enum
2. Create migration
3. Seed initial document via migration or admin UI

### Modifying Membership Status Logic
Update `Profile.ComputeMembershipStatus()` method. Add tests for all edge cases.

### Adding Google Resource Access
1. Create GoogleResource record
2. Link to Role via RoleGoogleAccess or Team via TeamGoogleAccess
3. Reconciliation job will grant access on next run

## Security Considerations

- Use ASP.NET Core Data Protection for encryption
- Store secrets in Azure Key Vault, AWS Secrets Manager, or user-secrets (dev)
- Implement CSRF protection (enabled by default)
- Use Content Security Policy headers
- Sanitize HTML content from legal documents before rendering
- Rate limit authentication endpoints
- Log security events with Serilog
