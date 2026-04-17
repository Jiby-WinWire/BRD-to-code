"""C# .NET Code Generator - Produces production-ready ASP.NET Core + Entity Framework code"""

from typing import Dict, List, Any
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class CSharpCodeGenerator:
    """Generates production-ready C# .NET code from user stories"""
    
    @staticmethod
    def generate_from_stories(stories: List[Dict], llm_client, deployment_name: str) -> Dict[str, str]:
        """
        Generate C# .NET application files from stories
        
        Returns dict with file paths as keys and code content as values.
        Uses LLM if available, otherwise falls back to sample templates.
        """
        
        if not stories:
            logger.warning("No stories provided for C# code generation")
            return {}
        
        if not llm_client:
            logger.error("LLM client not configured. Set AZURE_OPENAI_API_KEY environment variable.")
            return {}
        
        functional_stories = [s for s in stories if isinstance(s, dict)]
        stories_to_process = functional_stories[:5] if functional_stories else stories[:5]
        
        # Try LLM generation first if client is available
        if llm_client is not None:
            result = CSharpCodeGenerator._generate_with_llm(stories_to_process, llm_client, deployment_name)
            if result:
                return result
            logger.warning("LLM generation failed, falling back to template generation")
        else:
            logger.info("⚠️  Azure OpenAI not configured, using template generation")
        
        # Fallback to template-based generation
        return CSharpCodeGenerator._generate_from_templates(stories_to_process)
    
    @staticmethod
    def _generate_with_llm(stories: List[Dict], llm_client, deployment_name: str) -> Dict[str, str]:
        """Generate using LLM (Azure OpenAI)"""
        try:
            # Build stories text
            stories_text = CSharpCodeGenerator._build_stories_text(stories)
            
            # System prompt for C# code generation
            system_prompt = CSharpCodeGenerator._get_system_prompt()
            
            prompt = f"""Generate a complete, production-ready ASP.NET Core web application for these requirements:

{stories_text}

Return a JSON object with these keys:
- "Entity": C# entity/model class
- "DbContext": Entity Framework DbContext
- "Service": Business logic service class
- "Controller": ASP.NET Core MVC Controller
- "Index": Razor view (.cshtml)
- "Edit": Edit view for update operations (.cshtml)
- "Create": Create view for add operations (.cshtml)
- "SiteCSS": CSS styling for the application
- "SiteJS": JavaScript for interactivity
- "appsettings": appsettings.json configuration
- "Startup": Startup.cs or Program.cs (use modern minimal hosting API)
- "Migrations": EF Core migration class
- "README": Setup and run instructions

Each value should contain production-ready code."""
            
            logger.info(f"Generating C#/.NET application for {len(stories)} stories using LLM...")
            
            response = llm_client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=8000,
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content
            generated_code = json.loads(response_text)
            
            # Map generated code to file structure
            file_structure = CSharpCodeGenerator._map_to_files(generated_code)
            
            logger.info(f"C# code generation complete. Generated {len(file_structure)} files")
            return file_structure
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse C# generator response as JSON: {str(e)}")
            return {}
        except AttributeError as e:
            logger.error(f"LLM client error (API key not configured?): {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"C# LLM generation failed: {str(e)}")
            return {}
    
    @staticmethod
    def _generate_from_templates(stories: List[Dict]) -> Dict[str, str]:
        """Generate using built-in templates (no LLM required)"""
        try:
            logger.info("Using template-based generation (no LLM required)")
            
            # Load sample files if they exist
            sample_path = Path(__file__).parent.parent.parent.parent / "output" / "csharp-sample"
            
            if sample_path.exists():
                logger.info(f"Loading templates from {sample_path}")
                return CSharpCodeGenerator._load_template_files(sample_path)
            else:
                logger.info("Using hardcoded templates")
                return CSharpCodeGenerator._get_hardcoded_templates()
                
        except Exception as e:
            logger.error(f"Template generation failed: {str(e)}")
            return {}
    
    @staticmethod
    def _load_template_files(template_path: Path) -> Dict[str, str]:
        """Load templates from existing sample files"""
        files = {}
        
        file_mappings = {
            "Models/Todo.cs": "Models/Todo.cs",
            "Data/ApplicationDbContext.cs": "Data/ApplicationDbContext.cs",
            "Services/TodoService.cs": "Services/TodoService.cs",
            "Controllers/TodosController.cs": "Controllers/TodosController.cs",
            "Views/Todos/Index.cshtml": "Views/Index.cshtml",
            "wwwroot/js/site.js": "wwwroot/js/site.js",
            "wwwroot/css/site.css": "wwwroot/css/site.css",
            "Program.cs": "Program.cs",
            "appsettings.json": "appsettings.json",
            "TodoApp.csproj": "TodoApp.csproj",
        }
        
        for output_path, template_path_str in file_mappings.items():
            full_path = template_path / template_path_str
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        files[output_path] = f.read()
                    logger.info(f"  ✓ Loaded: {output_path}")
                except Exception as e:
                    logger.warning(f"  ✗ Failed to load {output_path}: {str(e)}")
        
        return files if files else CSharpCodeGenerator._get_hardcoded_templates()
    
    @staticmethod
    def _get_hardcoded_templates() -> Dict[str, str]:
        """Return hardcoded minimal templates as last resort"""
        logger.info("Using minimal hardcoded templates")
        
        return {
            "Models/Todo.cs": """using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace TodoApp.Models
{
    /// <summary>
    /// Todo entity model with validation attributes
    /// </summary>
    [Table("Todos")]
    public class Todo
    {
        [Key]
        [DatabaseGenerated(DatabaseGeneratedOption.Identity)]
        public int Id { get; set; }

        [Required(ErrorMessage = "Title is required")]
        [StringLength(200, MinimumLength = 1)]
        public string Title { get; set; }

        [StringLength(1000)]
        public string Description { get; set; }

        [Required]
        [StringLength(20)]
        public string Status { get; set; } = "pending";

        [Range(1, 5)]
        public int Priority { get; set; } = 1;

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
        public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    }
}
""",
            "Data/ApplicationDbContext.cs": """using Microsoft.EntityFrameworkCore;
using TodoApp.Models;

namespace TodoApp.Data
{
    /// <summary>
    /// Entity Framework Core DbContext for Todo application
    /// </summary>
    public class ApplicationDbContext : DbContext
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
        }

        public DbSet<Todo> Todos { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            modelBuilder.Entity<Todo>(entity =>
            {
                entity.HasKey(e => e.Id);
                entity.ToTable("Todos");

                entity.Property(e => e.Title)
                    .IsRequired()
                    .HasMaxLength(200);

                entity.Property(e => e.Description)
                    .HasMaxLength(1000);

                entity.Property(e => e.Status)
                    .IsRequired()
                    .HasMaxLength(20)
                    .HasDefaultValue("pending");

                entity.Property(e => e.Priority)
                    .IsRequired()
                    .HasDefaultValue(1);

                entity.Property(e => e.CreatedAt)
                    .IsRequired()
                    .ValueGeneratedOnAdd();

                entity.Property(e => e.UpdatedAt)
                    .IsRequired()
                    .ValueGeneratedOnAddOrUpdate();

                entity.HasIndex(e => e.Status).HasName("IX_Todos_Status");
                entity.HasIndex(e => e.CreatedAt).HasName("IX_Todos_CreatedAt");
            });
        }
    }
}
""",
            "Services/TodoService.cs": """using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using TodoApp.Data;
using TodoApp.Models;

namespace TodoApp.Services
{
    public interface ITodoService
    {
        Task<Todo> CreateAsync(Todo todo);
        Task<Todo> GetByIdAsync(int id);
        Task<List<Todo>> GetAllAsync(string status = null);
        Task<Todo> UpdateAsync(int id, Todo todo);
        Task<bool> DeleteAsync(int id);
        Task<(int Total, int Completed, int Pending)> GetStatsAsync();
    }

    public class TodoService : ITodoService
    {
        private readonly ApplicationDbContext _context;
        private readonly ILogger<TodoService> _logger;

        public TodoService(ApplicationDbContext context, ILogger<TodoService> logger)
        {
            _context = context ?? throw new ArgumentNullException(nameof(context));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        public async Task<Todo> CreateAsync(Todo todo)
        {
            if (todo == null) throw new ArgumentNullException(nameof(todo));
            
            _context.Todos.Add(todo);
            await _context.SaveChangesAsync();
            _logger.LogInformation($"Created todo: {todo.Id}");
            return todo;
        }

        public async Task<Todo> GetByIdAsync(int id)
        {
            return await _context.Todos.FindAsync(id);
        }

        public async Task<List<Todo>> GetAllAsync(string status = null)
        {
            var query = _context.Todos.AsQueryable();
            
            if (!string.IsNullOrEmpty(status))
                query = query.Where(t => t.Status == status.ToLower());
            
            return await query.OrderByDescending(t => t.Priority).ThenBy(t => t.Id).ToListAsync();
        }

        public async Task<Todo> UpdateAsync(int id, Todo todo)
        {
            var existing = await _context.Todos.FindAsync(id);
            if (existing == null) return null;

            existing.Title = todo.Title ?? existing.Title;
            existing.Description = todo.Description ?? existing.Description;
            existing.Status = todo.Status ?? existing.Status;
            existing.Priority = todo.Priority;
            existing.UpdatedAt = DateTime.UtcNow;

            await _context.SaveChangesAsync();
            _logger.LogInformation($"Updated todo: {id}");
            return existing;
        }

        public async Task<bool> DeleteAsync(int id)
        {
            var todo = await _context.Todos.FindAsync(id);
            if (todo == null) return false;

            _context.Todos.Remove(todo);
            await _context.SaveChangesAsync();
            _logger.LogInformation($"Deleted todo: {id}");
            return true;
        }

        public async Task<(int Total, int Completed, int Pending)> GetStatsAsync()
        {
            var total = await _context.Todos.CountAsync();
            var completed = await _context.Todos.CountAsync(t => t.Status == "completed");
            var pending = total - completed;
            return (total, completed, pending);
        }
    }
}
""",
            "Program.cs": """using Microsoft.AspNetCore.Builder;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using TodoApp.Data;
using TodoApp.Services;

namespace TodoApp
{
    public class Program
    {
        public static void Main(string[] args)
        {
            var builder = WebApplication.CreateBuilder(args);

            builder.WebHost.ConfigureKestrel(serverOptions =>
            {
                serverOptions.Listen(System.Net.IPAddress.Parse("0.0.0.0"), 7000);
            });

            var connectionString = builder.Configuration.GetConnectionString("DefaultConnection") 
                ?? "Data Source=todo.db";
            
            builder.Services.AddDbContext<ApplicationDbContext>(options =>
                options.UseSqlite(connectionString)
            );

            builder.Services.AddScoped<ITodoService, TodoService>();
            builder.Services.AddLogging();
            builder.Services.AddControllers();
            builder.Services.AddEndpointsApiExplorer();
            builder.Services.AddSwaggerGen();
            builder.Services.AddCors(options =>
            {
                options.AddPolicy("AllowAll", builder =>
                {
                    builder.AllowAnyOrigin()
                           .AllowAnyMethod()
                           .AllowAnyHeader();
                });
            });

            var app = builder.Build();

            if (app.Environment.IsDevelopment())
            {
                app.UseSwagger();
                app.UseSwaggerUI();
                app.UseDeveloperExceptionPage();
            }

            app.UseCors("AllowAll");
            app.UseAuthorization();
            app.MapControllers();

            // Initialize database with fallback strategy
            using (var scope = app.Services.CreateScope())
            {
                try
                {
                    var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
                    dbContext.Database.Migrate();
                    Console.WriteLine("✓ Database migrations applied");
                }
                catch (Exception ex)
                {
                    try
                    {
                        var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
                        dbContext.Database.EnsureCreated();
                        Console.WriteLine("✓ Database created using EnsureCreated");
                    }
                    catch (Exception fallbackEx)
                    {
                        Console.WriteLine($"⚠️  Database initialization failed: {fallbackEx.Message}");
                    }
                }
            }

            Console.WriteLine("🚀 Starting application on http://localhost:7000");
            app.Run();
        }
    }
}
""",
            "appsettings.json": """{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.EntityFrameworkCore": "Warning"
    }
  },
  "ConnectionStrings": {
    "DefaultConnection": "Data Source=todo.db"
  },
  "AllowedHosts": "*"
}
""",
        }
    
    @staticmethod
    def _build_stories_text(stories: List[Dict]) -> str:
        """Build formatted stories text"""
        parts = []
        for i, story in enumerate(stories, 1):
            if isinstance(story, dict):
                summary = story.get('summary') or story.get('title', '')
                description = (story.get('description', '')[:200]).strip()
            else:
                summary = str(story)
                description = ""
            
            parts.append(f"{i}. {summary}: {description}")
        
        return "\n".join(parts)
    
    @staticmethod
    def _get_system_prompt() -> str:
        """Get system prompt for C# code generation"""
        return """You are an expert C# .NET developer with 15+ years experience building enterprise applications.
Generate a complete, production-ready ASP.NET Core MVC web application with:

ARCHITECTURE:
- Entity Framework Core ORM with SQL Server/SQLite support
- Dependency Injection via built-in Microsoft.Extensions.DependencyInjection
- MVC pattern: Models → Services → Controllers → Views
- Repository pattern for data access
- Async/await throughout the codebase

CODE STANDARDS:
- Use modern C# 12+ features (nullable reference types, records, patterns)
- All methods async (Task, Task<T>)
- Proper exception handling with custom exceptions
- Logging via ILogger<T>
- Configuration via appsettings.json
- HTTPGET, HTTPPOST, etc. attributes for routing
- Fluent API for EF Core mappings
- Input validation via DataAnnotations

DATABASE:
- Entity Framework Core with DbContext
- Use HasMany().WithOne() fluent API
- Configure cascading deletes appropriately
- Add migration files
- Support both SQLite (dev) and SQL Server (prod)

CONTROLLERS:
- Use [Controller] attribute
- Use [HttpGet], [HttpPost], [HttpPut], [HttpDelete] attributes
- Return IActionResult (Ok(), NotFound(), BadRequest(), CreatedAtAction())
- Inject ILogger<T> and service interfaces
- Implement CRUD operations with proper status codes

VIEWS (Razor):
- Use Bootstrap 5 for responsive UI
- Implement forms with form helpers @Html.TextBoxFor(), etc.
- Add client-side validation with unobtrusive JavaScript
- Create CRUD views: Index, Create, Edit, Delete
- Use layouts with @RenderBody()
- Display validation errors

JAVASCRIPT:
- Use fetch() for API calls (if exposing API endpoints)
- jQuery for DOM manipulation
- Form validation before submission
- Loading indicators
- Error handling and user feedback

CONFIGURATION:
- appsettings.json with connection string
- Logging configuration
- CORS if needed
- Static files configuration

CRITICAL REQUIREMENTS:
- Generation must return valid JSON ONLY
- All code must compile without errors
- Must follow C# naming conventions (PascalCase for classes, camelCase for properties)
- Include XML documentation comments for public members
- Use dependency injection throughout
- Implement IDisposable where needed
- Use using statements for resource management

Return ONLY a JSON object with the specified keys. Each value is pure C# code or configuration."""
    
    @staticmethod
    def _map_to_files(generated_code: Dict[str, str]) -> Dict[str, str]:
        """Map generated code to file structure"""
        file_mapping = {
            "Models/Entity.cs": generated_code.get("Entity", ""),
            "Data/ApplicationDbContext.cs": generated_code.get("DbContext", ""),
            "Services/EntityService.cs": generated_code.get("Service", ""),
            "Controllers/EntityController.cs": generated_code.get("Controller", ""),
            "Views/Index.cshtml": generated_code.get("Index", ""),
            "Views/Edit.cshtml": generated_code.get("Edit", ""),
            "Views/Create.cshtml": generated_code.get("Create", ""),
            "wwwroot/css/site.css": generated_code.get("SiteCSS", ""),
            "wwwroot/js/site.js": generated_code.get("SiteJS", ""),
            "appsettings.json": generated_code.get("appsettings", ""),
            "Program.cs": generated_code.get("Startup", ""),
            "Migrations/001_InitialCreate.cs": generated_code.get("Migrations", ""),
        }
        
        # Filter out empty entries
        return {k: v for k, v in file_mapping.items() if v}
