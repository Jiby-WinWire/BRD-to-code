# Jira user stories to ASP.NET Core C# code generation logic using LLM
from typing import List, Dict
import logging
import json
from pathlib import Path
from src.infrastructure.azure_clients import get_llm_client, get_llm_deployment_name

logger = logging.getLogger(__name__)

def stories_to_csharp_code(stories: List[Dict]) -> Dict[str, str]:
    """
    Generate functional ASP.NET Core C# code files from Jira user stories.
    Uses LLM if available, otherwise falls back to sample templates.
    Returns a dict mapping file paths to file contents.
    """
    if not stories:
        logger.warning("No stories provided for C# code generation")
        return {}
    
    llm = get_llm_client()
    deployment_name = get_llm_deployment_name()
    
    # Group stories by type for better code generation
    functional_stories = []
    for s in stories:
        if 'fields' in s:
            if 'functional' in s['fields'].get('labels', []):
                functional_stories.append(s)
        else:
            functional_stories.append(s)
    
    stories_to_process = functional_stories[:5] if functional_stories else stories[:5]
    
    # Try LLM first if available
    if llm is not None:
        result = _generate_with_llm(stories_to_process, llm, deployment_name)
        if result:
            return result
        logger.warning("LLM generation failed, falling back to templates")
    else:
        logger.info("⚠️  Azure OpenAI not configured, using template generation")
    
    # Fallback to template-based generation
    return _generate_from_templates(stories_to_process)


def _generate_with_llm(stories_to_process: List[Dict], llm, deployment_name: str) -> Dict[str, str]:
    """Generate code using LLM (Azure OpenAI)"""
    system_prompt = """You are an expert C# ASP.NET Core developer. Generate a complete, production-ready ASP.NET Core web application.

Generate a COMPLETE ASP.NET Core 8 application with these EXACT files:

MODELS & DATABASE:
1. Models/EntityName.cs - Entity Framework Core models with data annotations
2. Data/ApplicationDbContext.cs - DbContext for Entity Framework
3. Data/DbInitializer.cs - Database initialization with seed data

SERVICES & BUSINESS LOGIC:
4. Services/IEntityService.cs - Service interface
5. Services/EntityService.cs - Service implementation with dependency injection

CONTROLLERS & API:
6. Controllers/EntityController.cs - ASP.NET Core API controller with full CRUD endpoints
7. Controllers/HomeController.cs - Home controller serving UI

VIEWS & UI:
8. Views/Index.cshtml - Main view with Razor templating
9. Views/Shared/_Layout.cshtml - Shared layout template
10. wwwroot/css/site.css - Bootstrap 5 styles

CONFIGURATION:
11. Program.cs - Minimal hosting API with services, middleware, routing
12. appsettings.json - Configuration settings
13. TodoApp.csproj - Project file with dependencies

CRITICAL REQUIREMENTS FOR EACH FILE:

**Models/EntityName.cs MUST:**
- Use namespace TodoApp.Models
- Have [Table("EntityNames")] attribute
- Have [Key] and [DatabaseGenerated(DatabaseGeneratedOption.Identity)] on Id
- Have [Required] on required fields
- Have [StringLength(200)] on string fields
- Include CreatedAt and UpdatedAt timestamps
- Use DateTime.UtcNow as defaults

**Data/ApplicationDbContext.cs MUST:**
- Inherit from DbContext
- Have public DbSet<Entity> Entities { get; set; }
- Implement OnModelCreating with fluent API configuration
- Include indexes on frequently queried columns
- Use namespace TodoApp.Data

**Services/IEntityService.cs MUST:**
- Define async CRUD methods: CreateAsync, GetByIdAsync, GetAllAsync, UpdateAsync, DeleteAsync
- Return proper types (Task<Entity>, Task<List<Entity>>)
- Use namespace TodoApp.Services

**Services/EntityService.cs MUST:**
- Implement IEntityService interface
- Use dependency injection for ApplicationDbContext
- Use Entity Framework async operations (SaveChangesAsync)
- Include proper logging with ILogger<EntityService>
- Handle null checks and validation

**Controllers/EntityController.cs MUST:**
- Use [ApiController] and [Route("api/[controller]")] attributes
- Implement GET, POST, PUT, DELETE endpoints
- Accept Pydantic-style request bodies as single entity parameters
- Return proper HTTP status codes: 201 for POST, 404 for not found, 200 for success
- Use dependency injection for IEntityService
- Include XML documentation comments
- Use async/await throughout

**Controllers/HomeController.cs MUST:**
- Have [HttpGet] [Route("")] to serve Index.cshtml at root
- Return PhysicalFile for wwwroot/index.html as fallback

**Program.cs MUST:**
- Use builder.Services.AddDbContext with UseSqlite
- Include builder.Services.AddScoped<IEntityService, EntityService>
- Add Swagger/OpenAPI support
- Add CORS with AllowAll policy  
- Map controllers with app.MapControllers()
- Include /health endpoint returning JSON
- Include database initialization code
- Configure Kestrel to listen on 0.0.0.0:7000

**Views/Index.cshtml MUST:**
- Use Bootstrap 5 for styling
- Include form to CREATE items
- Include table/cards to display items
- Include buttons for UPDATE/DELETE with JavaScript
- Use Jinja2-style rendering with C# Razor syntax (@Model, @foreach, etc)

**wwwroot/css/site.css MUST:**
- Include Bootstrap 5 CDN import
- Professional styling with good color scheme
- Responsive grid layouts

Return ONLY valid JSON with these keys (NO MARKDOWN, NO EXPLANATIONS):
{
  "Models/Todo.cs": "...",
  "Data/ApplicationDbContext.cs": "...",
  "Services/ITodoService.cs": "...",
  "Services/TodoService.cs": "...",
  "Controllers/TodosController.cs": "...",
  "Controllers/HomeController.cs": "...",
  "Views/Index.cshtml": "...",
  "Views/Shared/_Layout.cshtml": "...",
  "wwwroot/css/site.css": "...",
  "Program.cs": "...",
  "appsettings.json": "...",
  "TodoApp.csproj": "..."
}"""
    
    # Build stories text
    stories_text_parts = []
    for i, s in enumerate(stories_to_process):
        if 'fields' in s:
            # JIRA format
            summary = s['fields'].get('summary', '')
            description = s['fields'].get('description', '')[:200]
        else:
            # Simple format
            summary = s.get('title', s.get('id', ''))
            description = s.get('description', '')[:200]
        stories_text_parts.append(f"{i+1}. {summary}: {description}")
    
    stories_text = "\n".join(stories_text_parts)
    
    prompt = f"""Generate a complete ASP.NET Core 8 web application for these user stories:

{stories_text}

Create production-ready code that will compile without errors and run successfully.
Ensure all files are complete with proper namespaces, using statements, and implementations."""
    
    try:
        logger.info(f"Generating C#/.NET application for {len(stories_to_process)} stories using LLM...")
        
        response = llm.chat.completions.create(
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
        
        # Map to proper file structure
        file_structure = {}
        for key, value in generated_code.items():
            if isinstance(value, str) and value.strip():
                file_structure[key] = value
        
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


def _generate_from_templates(stories_to_process: List[Dict]) -> Dict[str, str]:
    """Generate using built-in production-ready templates"""
    logger.info("Generating C# project from production templates")
    
    return {
        "Models/Todo.cs": """using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace TodoApp.Models
{
    /// <summary>
    /// Todo entity model representing a task to be completed
    /// </summary>
    [Table("Todos")]
    public class Todo
    {
        /// <summary>
        /// Unique identifier for the todo
        /// </summary>
        [Key]
        [DatabaseGenerated(DatabaseGeneratedOption.Identity)]
        public int Id { get; set; }

        /// <summary>
        /// Title of the todo - required field
        /// </summary>
        [Required(ErrorMessage = "Title is required")]
        [StringLength(200, MinimumLength = 1, ErrorMessage = "Title must be between 1 and 200 characters")]
        public string Title { get; set; }

        /// <summary>
        /// Detailed description of the todo - optional
        /// </summary>
        [StringLength(1000, ErrorMessage = "Description cannot exceed 1000 characters")]
        public string Description { get; set; }

        /// <summary>
        /// Current status: pending, completed, or archived
        /// </summary>
        [Required]
        [StringLength(20)]
        [RegularExpression("^(pending|completed|archived)$", ErrorMessage = "Status must be pending, completed, or archived")]
        public string Status { get; set; } = "pending";

        /// <summary>
        /// Priority level from 1 (low) to 5 (urgent)
        /// </summary>
        [Range(1, 5, ErrorMessage = "Priority must be between 1 and 5")]
        public int Priority { get; set; } = 1;

        /// <summary>
        /// Creation timestamp
        /// </summary>
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        /// <summary>
        /// Last modification timestamp
        /// </summary>
        public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

        /// <summary>
        /// Computed property: checks if todo is completed
        /// </summary>
        [NotMapped]
        public bool IsCompleted => Status == "completed";
    }
}
""",
        "Data/ApplicationDbContext.cs": """using Microsoft.EntityFrameworkCore;
using TodoApp.Models;

namespace TodoApp.Data
{
    /// <summary>
    /// Entity Framework Core DbContext for the Todo application
    /// Manages database configuration and entity mappings
    /// </summary>
    public class ApplicationDbContext : DbContext
    {
        /// <summary>
        /// Constructor with dependency injection of DbContext options
        /// </summary>
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
        }

        /// <summary>
        /// DbSet representing the Todos table
        /// </summary>
        public DbSet<Todo> Todos { get; set; }

        /// <summary>
        /// Configure entity relationships, constraints, and indexes
        /// </summary>
        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            // Configure Todo entity
            modelBuilder.Entity<Todo>(entity =>
            {
                entity.HasKey(e => e.Id);
                entity.ToTable("Todos");

                // Configure Title property
                entity.Property(e => e.Title)
                    .IsRequired()
                    .HasMaxLength(200);

                // Configure Description property
                entity.Property(e => e.Description)
                    .HasMaxLength(1000);

                // Configure Status property
                entity.Property(e => e.Status)
                    .IsRequired()
                    .HasMaxLength(20)
                    .HasDefaultValue("pending");

                // Configure Priority property
                entity.Property(e => e.Priority)
                    .IsRequired()
                    .HasDefaultValue(1);

                // Configure timestamps
                entity.Property(e => e.CreatedAt)
                    .IsRequired()
                    .ValueGeneratedOnAdd();

                entity.Property(e => e.UpdatedAt)
                    .IsRequired()
                    .ValueGeneratedOnAddOrUpdate();

                // Add indexes for performance
                entity.HasIndex(e => e.Status).HasName("IX_Todos_Status");
                entity.HasIndex(e => e.Priority).HasName("IX_Todos_Priority");
                entity.HasIndex(e => e.CreatedAt).HasName("IX_Todos_CreatedAt");
            });
        }
    }
}
""",
        "Services/ITodoService.cs": """using TodoApp.Models;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace TodoApp.Services
{
    /// <summary>
    /// Service interface for Todo business logic operations
    /// </summary>
    public interface ITodoService
    {
        /// <summary>
        /// Create a new todo asynchronously
        /// </summary>
        Task<Todo> CreateAsync(Todo todo);

        /// <summary>
        /// Get a todo by ID asynchronously
        /// </summary>
        Task<Todo> GetByIdAsync(int id);

        /// <summary>
        /// Get all todos, optionally filtered by status
        /// </summary>
        Task<List<Todo>> GetAllAsync(string? status = null);

        /// <summary>
        /// Update an existing todo
        /// </summary>
        Task<Todo> UpdateAsync(int id, Todo todo);

        /// <summary>
        /// Delete a todo by ID
        /// </summary>
        Task<bool> DeleteAsync(int id);

        /// <summary>
        /// Mark a todo as completed
        /// </summary>
        Task<Todo> MarkCompleteAsync(int id);

        /// <summary>
        /// Get statistics about todos
        /// </summary>
        Task<(int Total, int Completed, int Pending)> GetStatsAsync();
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
    /// <summary>
    /// Service implementation for Todo business logic
    /// Handles CRUD operations and business rules
    /// </summary>
    public class TodoService : ITodoService
    {
        private readonly ApplicationDbContext _context;
        private readonly ILogger<TodoService> _logger;

        /// <summary>
        /// Constructor with dependency injection
        /// </summary>
        public TodoService(ApplicationDbContext context, ILogger<TodoService> logger)
        {
            _context = context ?? throw new ArgumentNullException(nameof(context));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <summary>
        /// Create a new todo asynchronously
        /// </summary>
        public async Task<Todo> CreateAsync(Todo todo)
        {
            if (todo == null)
                throw new ArgumentNullException(nameof(todo));

            if (string.IsNullOrWhiteSpace(todo.Title))
                throw new ArgumentException("Title is required", nameof(todo));

            todo.CreatedAt = DateTime.UtcNow;
            todo.UpdatedAt = DateTime.UtcNow;

            _context.Todos.Add(todo);
            await _context.SaveChangesAsync();

            _logger.LogInformation($"Todo created: Id={todo.Id}, Title={todo.Title}");
            return todo;
        }

        /// <summary>
        /// Get a todo by ID asynchronously
        /// </summary>
        public async Task<Todo> GetByIdAsync(int id)
        {
            var todo = await _context.Todos.FindAsync(id);
            
            if (todo == null)
            {
                _logger.LogWarning($"Todo not found: {id}");
            }

            return todo;
        }

        /// <summary>
        /// Get all todos, optionally filtered by status
        /// </summary>
        public async Task<List<Todo>> GetAllAsync(string? status = null)
        {
            IQueryable<Todo> query = _context.Todos;

            if (!string.IsNullOrEmpty(status))
            {
                query = query.Where(t => t.Status == status);
            }

            var todos = await query
                .OrderByDescending(t => t.Priority)
                .ThenByDescending(t => t.CreatedAt)
                .ToListAsync();

            _logger.LogInformation($"Retrieved {todos.Count} todos" + 
                (string.IsNullOrEmpty(status) ? "" : $" with status={status}"));
            
            return todos;
        }

        /// <summary>
        /// Update an existing todo
        /// </summary>
        public async Task<Todo> UpdateAsync(int id, Todo todo)
        {
            var existingTodo = await _context.Todos.FindAsync(id);
            
            if (existingTodo == null)
            {
                _logger.LogWarning($"Todo not found for update: {id}");
                return null;
            }

            existingTodo.Title = todo.Title ?? existingTodo.Title;
            existingTodo.Description = todo.Description ?? existingTodo.Description;
            existingTodo.Status = todo.Status ?? existingTodo.Status;
            existingTodo.Priority = todo.Priority > 0 ? todo.Priority : existingTodo.Priority;
            existingTodo.UpdatedAt = DateTime.UtcNow;

            await _context.SaveChangesAsync();

            _logger.LogInformation($"Todo updated: Id={id}");
            return existingTodo;
        }

        /// <summary>
        /// Delete a todo by ID
        /// </summary>
        public async Task<bool> DeleteAsync(int id)
        {
            var todo = await _context.Todos.FindAsync(id);
            
            if (todo == null)
            {
                _logger.LogWarning($"Todo not found for deletion: {id}");
                return false;
            }

            _context.Todos.Remove(todo);
            await _context.SaveChangesAsync();

            _logger.LogInformation($"Todo deleted: {id}");
            return true;
        }

        /// <summary>
        /// Mark a todo as completed
        /// </summary>
        public async Task<Todo> MarkCompleteAsync(int id)
        {
            var todo = await _context.Todos.FindAsync(id);
            
            if (todo == null)
            {
                _logger.LogWarning($"Todo not found: {id}");
                return null;
            }

            todo.Status = "completed";
            todo.UpdatedAt = DateTime.UtcNow;

            await _context.SaveChangesAsync();

            _logger.LogInformation($"Todo marked complete: {id}");
            return todo;
        }

        /// <summary>
        /// Get statistics about todos
        /// </summary>
        public async Task<(int Total, int Completed, int Pending)> GetStatsAsync()
        {
            var todos = await _context.Todos.ToListAsync();
            int total = todos.Count;
            int completed = todos.Count(t => t.Status == "completed");
            int pending = todos.Count(t => t.Status == "pending");

            return (total, completed, pending);
        }
    }
}
""",
        "Controllers/TodosController.cs": """using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using TodoApp.Models;
using TodoApp.Services;

namespace TodoApp.Controllers
{
    /// <summary>
    /// API Controller for Todo operations
    /// Provides RESTful endpoints for CRUD operations on todos
    /// </summary>
    [ApiController]
    [Route("api/[controller]")]
    [Produces("application/json")]
    public class TodosController : ControllerBase
    {
        private readonly ITodoService _todoService;
        private readonly ILogger<TodosController> _logger;

        /// <summary>
        /// Constructor with dependency injection
        /// </summary>
        public TodosController(ITodoService todoService, ILogger<TodosController> logger)
        {
            _todoService = todoService ?? throw new ArgumentNullException(nameof(todoService));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <summary>
        /// GET: api/todos
        /// Get all todos with optional status filter
        /// </summary>
        [HttpGet]
        [ProducesResponseType(typeof(List<Todo>), 200)]
        public async Task<ActionResult<List<Todo>>> GetAllTodos([FromQuery] string? status = null)
        {
            try
            {
                var todos = await _todoService.GetAllAsync(status);
                return Ok(todos);
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error getting todos: {ex.Message}");
                return StatusCode(500, new { error = "Failed to retrieve todos" });
            }
        }

        /// <summary>
        /// GET: api/todos/{id}
        /// Get a specific todo by ID
        /// </summary>
        [HttpGet("{id}")]
        [ProducesResponseType(typeof(Todo), 200)]
        [ProducesResponseType(404)]
        public async Task<ActionResult<Todo>> GetTodoById(int id)
        {
            try
            {
                var todo = await _todoService.GetByIdAsync(id);
                if (todo == null)
                    return NotFound(new { error = $"Todo with id {id} not found" });

                return Ok(todo);
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error getting todo {id}: {ex.Message}");
                return StatusCode(500, new { error = "Failed to retrieve todo" });
            }
        }

        /// <summary>
        /// POST: api/todos
        /// Create a new todo
        /// </summary>
        [HttpPost]
        [ProducesResponseType(typeof(Todo), 201)]
        [ProducesResponseType(400)]
        public async Task<ActionResult<Todo>> CreateTodo([FromBody] Todo todo)
        {
            try
            {
                // Null check for request body
                if (todo == null)
                    return BadRequest(new { error = "Todo object is required" });

                // Validate model state
                if (!ModelState.IsValid)
                    return BadRequest(new { error = "Invalid todo data", details = ModelState.Values.SelectMany(v => v.Errors) });

                // Validate required Title field
                if (string.IsNullOrWhiteSpace(todo.Title))
                    return BadRequest(new { error = "Todo title is required" });

                var created = await _todoService.CreateAsync(todo);
                return CreatedAtAction(nameof(GetTodoById), new { id = created.Id }, created);
            }
            catch (ArgumentException ex)
            {
                _logger.LogWarning($"Invalid todo data: {ex.Message}");
                return BadRequest(new { error = "Invalid data: " + ex.Message });
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error creating todo: {ex.Message}");
                return StatusCode(500, new { error = "Failed to create todo", details = ex.Message });
            }
        }

        /// <summary>
        /// PUT: api/todos/{id}
        /// Update an existing todo
        /// </summary>
        [HttpPut("{id}")]
        [ProducesResponseType(typeof(Todo), 200)]
        [ProducesResponseType(404)]
        [ProducesResponseType(400)]
        public async Task<ActionResult<Todo>> UpdateTodo(int id, [FromBody] Todo todo)
        {
            try
            {
                if (!ModelState.IsValid)
                    return BadRequest(ModelState);

                var updated = await _todoService.UpdateAsync(id, todo);
                if (updated == null)
                    return NotFound(new { error = $"Todo with id {id} not found" });

                return Ok(updated);
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error updating todo {id}: {ex.Message}");
                return StatusCode(500, new { error = "Failed to update todo" });
            }
        }

        /// <summary>
        /// DELETE: api/todos/{id}
        /// Delete a todo
        /// </summary>
        [HttpDelete("{id}")]
        [ProducesResponseType(204)]
        [ProducesResponseType(404)]
        public async Task<ActionResult> DeleteTodo(int id)
        {
            try
            {
                var deleted = await _todoService.DeleteAsync(id);
                if (!deleted)
                    return NotFound(new { error = $"Todo with id {id} not found" });

                return NoContent();
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error deleting todo {id}: {ex.Message}");
                return StatusCode(500, new { error = "Failed to delete todo" });
            }
        }

        /// <summary>
        /// POST: api/todos/{id}/complete
        /// Mark a todo as completed
        /// </summary>
        [HttpPost("{id}/complete")]
        [ProducesResponseType(typeof(Todo), 200)]
        [ProducesResponseType(404)]
        public async Task<ActionResult<Todo>> MarkComplete(int id)
        {
            try
            {
                var completed = await _todoService.MarkCompleteAsync(id);
                if (completed == null)
                    return NotFound(new { error = $"Todo with id {id} not found" });

                return Ok(completed);
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error marking todo as complete: {ex.Message}");
                return StatusCode(500, new { error = "Failed to mark todo as complete" });
            }
        }

        /// <summary>
        /// GET: api/todos/stats/summary
        /// Get todo statistics
        /// </summary>
        [HttpGet("stats/summary")]
        [ProducesResponseType(typeof(object), 200)]
        public async Task<ActionResult> GetStats()
        {
            try
            {
                var (total, completed, pending) = await _todoService.GetStatsAsync();
                return Ok(new { total, completed, pending });
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error getting stats: {ex.Message}");
                return StatusCode(500, new { error = "Failed to retrieve stats" });
            }
        }
    }
}
""",
        "Controllers/HomeController.cs": """using Microsoft.AspNetCore.Mvc;

namespace TodoApp.Controllers
{
    /// <summary>
    /// Home Controller - Handles static file serving
    /// Redirects to API info for root requests
    /// Static files (index.html, CSS, JS) are served automatically by UseDefaultFiles/UseStaticFiles middleware
    /// </summary>
    public class HomeController : ControllerBase
    {
        private readonly ILogger<HomeController> _logger;

        public HomeController(ILogger<HomeController> logger)
        {
            _logger = logger;
        }

        /// <summary>
        /// GET: / - Redirects to API info or serves index.html via middleware
        /// Note: This method is not called for "/" requests because app.UseDefaultFiles()
        /// serves wwwroot/index.html automatically before this controller is reached.
        /// This is a fallback for documentation purposes.
        /// </summary>
        [HttpGet]
        [Route("~/")]
        [ApiExplorerSettings(IgnoreApi = true)]
        public IActionResult Index()
        {
            _logger.LogInformation("Serving home page");
            
            // If UseDefaultFiles didn't serve index.html, serve it explicitly  
            var indexPath = Path.Combine(Directory.GetCurrentDirectory(), "wwwroot", "index.html");
            if (System.IO.File.Exists(indexPath))
            {
                var content = System.IO.File.ReadAllText(indexPath);
                return Content(content, "text/html");
            }
            
            // Fallback: return API info if index.html doesn't exist
            return Ok(new 
            {
                message = "Todo Application API",
                version = "1.0.0",
                documentation = "/swagger/ui",
                health = "/health",
                api_endpoint = "/api/todos",
                note = "Ensure wwwroot/index.html exists for static file serving"
            });
        }
    }
}
""",
        "Views/Index.cshtml": """@{
    ViewData["Title"] = "Todo Application";
}

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Todo Application</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="/css/site.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">📝 Todo App</a>
        </div>
    </nav>

    <div class="container mt-5">
        <div class="row">
            <div class="col-lg-8 mx-auto">
                <h1 class="mb-4">My Todos</h1>

                <!-- Add Todo Form -->
                <div class="card mb-4">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">Add New Todo</h5>
                    </div>
                    <div class="card-body">
                        <form id="addTodoForm">
                            <div class="mb-3">
                                <label for="title" class="form-label">Title</label>
                                <input type="text" class="form-control" id="title" required>
                            </div>
                            <div class="mb-3">
                                <label for="description" class="form-label">Description</label>
                                <textarea class="form-control" id="description" rows="3"></textarea>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label for="priority" class="form-label">Priority</label>
                                    <select class="form-select" id="priority">
                                        <option value="1">Low (1)</option>
                                        <option value="2">Medium (2)</option>
                                        <option value="3" selected>Normal (3)</option>
                                        <option value="4">High (4)</option>
                                        <option value="5">Urgent (5)</option>
                                    </select>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label for="status" class="form-label">Status</label>
                                    <select class="form-select" id="status">
                                        <option value="pending" selected>Pending</option>
                                        <option value="completed">Completed</option>
                                        <option value="archived">Archived</option>
                                    </select>
                                </div>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Add Todo</button>
                        </form>
                    </div>
                </div>

                <!-- Todos List -->
                <div id="todosContainer">
                    <div class="text-center text-muted">Loading todos...</div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/js/site.js"></script>
</body>
</html>
""",
        "Views/Shared/_Layout.cshtml": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@ViewData["Title"] - Todo App</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="/css/site.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">📝 Todo Application</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
        </div>
    </nav>

    <main>
        <div class="container">
            @RenderBody()
        </div>
    </main>

    <footer class="bg-light py-4 mt-5 border-top">
        <div class="container text-center text-muted">
            <p>&copy; 2024 Todo Application. Built with ASP.NET Core & Bootstrap.</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/js/site.js"></script>
</body>
</html>
""",
        "wwwroot/css/site.css": """/* Bootstrap 5 + Custom Styling */
@import url('https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css');

:root {
    --primary-color: #007bff;
    --success-color: #28a745;
    --danger-color: #dc3545;
    --warning-color: #ffc107;
    --dark-color: #343a40;
}

body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.container {
    background: white;
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.card {
    border: none;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
    border-radius: 8px;
    margin-bottom: 20px;
}

.card-header {
    border-radius: 8px 8px 0 0 !important;
    font-weight: 600;
    padding: 15px;
}

.btn {
    border-radius: 6px;
    font-weight: 500;
    transition: all 0.3s ease;
}

.btn-primary {
    background: var(--primary-color);
    border: none;
}

.btn-primary:hover {
    background: #0056b3;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.btn-success {
    background: var(--success-color);
    border: none;
}

.btn-danger {
    background: var(--danger-color);
    border: none;
}

.form-control, .form-select {
    border-radius: 6px;
    border: 1px solid #ddd;
    transition: all 0.3s ease;
}

.form-control:focus, .form-select:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

.todo-item {
    background: #f8f9fa;
    border-left: 4px solid var(--primary-color);
    padding: 15px;
    border-radius: 6px;
    margin-bottom: 12px;
    transition: all 0.3s ease;
}

.todo-item:hover {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    transform: translateX(4px);
}

.todo-item.completed {
    opacity: 0.7;
    background: #e8f5e9;
    border-left-color: var(--success-color);
}

.todo-item.completed .todo-title {
    text-decoration: line-through;
    color: #999;
}

.todo-title {
    font-size: 1.1em;
    font-weight: 600;
    color: var(--dark-color);
}

.todo-description {
    color: #666;
    margin-top: 8px;
    font-size: 0.95em;
}

.badge-priority {
    font-size: 0.8em;
    padding: 6px 10px;
}

.navbar {
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.navbar-brand {
    font-size: 1.5em;
    font-weight: 700;
}

footer {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid #eee;
}

h1 {
    color: var(--dark-color);
    font-weight: 700;
    margin-bottom: 30px;
}

.alert {
    border-radius: 6px;
    border: none;
    animation: slideIn 0.3s ease;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@media (max-width: 576px) {
    .container {
        padding: 12px;
    }
    
    h1 {
        font-size: 1.5em;
    }
    
    .card-body {
        padding: 12px;
    }
}
""",
        "wwwroot/js/site.js": """// Todo Application JavaScript

const API_BASE = '/api/todos';

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadTodos();
    setupFormHandler();
});

// Load all todos from API
async function loadTodos() {
    try {
        const response = await fetch(API_BASE);
        if (!response.ok) throw new Error('Failed to load todos');
        
        const todos = await response.json();
        renderTodos(todos);
    } catch (error) {
        console.error('Error loading todos:', error);
        showAlert('Failed to load todos', 'danger');
    }
}

// Render todos to the page
function renderTodos(todos) {
    const container = document.getElementById('todosContainer');
    
    if (!todos || todos.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No todos yet. Create one to get started!</div>';
        return;
    }
    
    container.innerHTML = todos.map(todo => `
        <div class="card todo-item ${todo.status === 'completed' ? 'completed' : ''}">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h5 class="todo-title">${escapeHtml(todo.title)}</h5>
                        ${todo.description ? `<p class="todo-description">${escapeHtml(todo.description)}</p>` : ''}
                        <div class="mt-2">
                            <span class="badge bg-secondary">${todo.status}</span>
                            <span class="badge ${getPriorityBadgeClass(todo.priority)}">Priority: ${todo.priority}</span>
                        </div>
                    </div>
                    <div class="btn-group" role="group">
                        ${todo.status !== 'completed' ? `
                            <button class="btn btn-sm btn-success" onclick="markComplete(${todo.id})">✓</button>
                        ` : ''}
                        <button class="btn btn-sm btn-warning" onclick="editTodo(${todo.id})">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteTodo(${todo.id})">Delete</button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

// Setup form submission
function setupFormHandler() {
    document.getElementById('addTodoForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const title = document.getElementById('title').value;
        const description = document.getElementById('description').value;
        const priority = parseInt(document.getElementById('priority').value);
        const status = document.getElementById('status').value;
        
        try {
            const response = await fetch(API_BASE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, description, priority, status })
            });
            
            if (!response.ok) throw new Error('Failed to create todo');
            
            this.reset();
            showAlert('Todo created successfully!', 'success');
            loadTodos();
        } catch (error) {
            console.error('Error:', error);
            showAlert('Failed to create todo', 'danger');
        }
    });
}

// Mark todo as complete
async function markComplete(id) {
    try {
        const response = await fetch(`${API_BASE}/${id}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) throw new Error('Failed to mark complete');
        showAlert('Todo marked as complete!', 'success');
        loadTodos();
    } catch (error) {
        console.error('Error:', error);
        showAlert('Failed to update todo', 'danger');
    }
}

// Delete todo
async function deleteTodo(id) {
    if (!confirm('Are you sure you want to delete this todo?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
        
        if (!response.ok) throw new Error('Failed to delete todo');
        showAlert('Todo deleted!', 'success');
        loadTodos();
    } catch (error) {
        console.error('Error:', error);
        showAlert('Failed to delete todo', 'danger');
    }
}

// Edit todo (placeholder)
function editTodo(id) {
    alert('Edit functionality coming soon!');
}

// Get priority badge class
function getPriorityBadgeClass(priority) {
    if (priority >= 4) return 'bg-danger';
    if (priority === 3) return 'bg-warning';
    return 'bg-info';
}

// Show alert message
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => alertDiv.remove(), 5000);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
    /// <summary>
    /// Application startup configuration
    /// Uses modern .NET 8 minimal hosting API
    /// </summary>
    public class Program
    {
        public static void Main(string[] args)
        {
            var builder = WebApplication.CreateBuilder(args);

            // ==================== Kestrel Configuration ====================
            
            // Configure Kestrel to listen on port 7000 (IPv4 only)
            builder.WebHost.ConfigureKestrel(serverOptions =>
            {
                serverOptions.Listen(System.Net.IPAddress.Parse("0.0.0.0"), 7000); // HTTP on port 7000
            });

            // ==================== Services Configuration ====================
            
            // Add DbContext with dependency injection
            var connectionString = builder.Configuration.GetConnectionString("DefaultConnection") 
                ?? "Data Source=todo.db";
            
            builder.Services.AddDbContext<ApplicationDbContext>(options =>
                options.UseSqlite(connectionString)
            );

            // Add services
            builder.Services.AddScoped<ITodoService, TodoService>();
            builder.Services.AddLogging();

            // Add controllers
            builder.Services.AddControllers();

            // Add Swagger/OpenAPI
            builder.Services.AddEndpointsApiExplorer();
            builder.Services.AddSwaggerGen(c =>
            {
                c.SwaggerDoc("v1", new()
                {
                    Title = "Todo API",
                    Version = "v1",
                    Description = "Production-ready Todo management API"
                });
            });

            // Add CORS
            builder.Services.AddCors(options =>
            {
                options.AddPolicy("AllowAll", builder =>
                {
                    builder.AllowAnyOrigin()
                           .AllowAnyMethod()
                           .AllowAnyHeader();
                });
            });

            // ==================== Build Application ====================
            
            var app = builder.Build();

            // ==================== Middleware Pipeline ====================
            
            // Development specific middleware
            if (app.Environment.IsDevelopment())
            {
                app.UseSwagger();
                app.UseSwaggerUI(c =>
                {
                    c.SwaggerEndpoint("/swagger/v1/swagger.json", "Todo API v1");
                    c.RoutePrefix = "swagger/ui";
                });
                app.UseDeveloperExceptionPage();
            }
            else
            {
                // Also enable Swagger in production for this demo app
                app.UseSwagger();
                app.UseSwaggerUI(c =>
                {
                    c.SwaggerEndpoint("/swagger/v1/swagger.json", "Todo API v1");
                    c.RoutePrefix = "swagger/ui";
                });
            }

            // Production middleware
            app.UseCors("AllowAll");
            
            // ==================== CRITICAL: Static Files BEFORE Routing ====================
            // Enable default files (serves index.html for "/" requests)
            app.UseDefaultFiles();
            
            // Enable static file serving (CSS, JS, images from wwwroot/)
            app.UseStaticFiles();
            
            // ==================== Routing & Authorization ====================
            app.UseRouting();
            app.UseAuthorization();

            // Map controllers (API routes)
            app.MapControllers();

            // API info endpoint (for /api/info requests, not /
            app.MapGet("/api/info", (HttpContext context) => new { 
                message = "Todo API", 
                version = "1.0.0", 
                time = DateTime.UtcNow,
                endpoints = new { 
                    todos = "/api/todos", 
                    health = "/health", 
                    swagger = "/swagger/ui",
                    ui = "/",
                    info = "/api/info"
                } 
            })
                .WithName("ApiInfo")
                .WithOpenApi();

            // Health check endpoint
            app.MapGet("/health", () => new { status = "healthy", version = "1.0.0", timestamp = DateTime.UtcNow })
                .WithName("Health")
                .WithOpenApi();

            // Initialize database on startup
            using (var scope = app.Services.CreateScope())
            {
                try
                {
                    var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
                    
                    // Try to run migrations if they exist
                    dbContext.Database.Migrate();
                    Console.WriteLine("✅ Database migration completed successfully");
                }
                catch (Exception ex)
                {
                    // Fallback: Create database schema directly if migrations don't exist
                    try
                    {
                        var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
                        dbContext.Database.EnsureCreated();
                        Console.WriteLine("✅ Database created successfully");
                    }
                    catch (Exception fallbackEx)
                    {
                        Console.WriteLine($"⚠️  Warning: Could not initialize database. Error: {fallbackEx.Message}");
                    }
                }
            }

            // ==================== Run Application ====================
            
            Console.WriteLine("🚀 Starting Todo Application...");
            Console.WriteLine("📝 API Documentation: http://localhost:7000/swagger/ui");
            Console.WriteLine("🏠 Home Page: http://localhost:7000/");
            Console.WriteLine("💚 Health Check: http://localhost:7000/health");
            Console.WriteLine("─────────────────────────────────────────────");
            
            app.Run();
        }
    }
}
""",
        "appsettings.json": """{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft": "Warning",
      "Microsoft.EntityFrameworkCore": "Information"
    }
  },
  "ConnectionStrings": {
    "DefaultConnection": "Data Source=todo.db"
  },
  "AllowedHosts": "*"
}
""",
        "TodoApp.csproj": """<Project Sdk="Microsoft.NET.Sdk.Web">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <LangVersion>latest</LangVersion>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.Sqlite" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.Tools" Version="8.0.0" />
    <PackageReference Include="Microsoft.AspNetCore.OpenApi" Version="8.0.0" />
    <PackageReference Include="Swashbuckle.AspNetCore" Version="6.4.6" />
  </ItemGroup>

</Project>
""",
        "RUN_INSTRUCTIONS.txt": """=== TODO APPLICATION - RUN INSTRUCTIONS ===

PREREQUISITES:
- .NET 8 SDK installed (download from https://dotnet.microsoft.com/download)
- Windows, macOS, or Linux

QUICK START:
1. dotnet restore     # Install dependencies
2. dotnet run         # Start the application

The application will be available at:
   📍 http://localhost:7000/

API ENDPOINTS:
   GET  /api/todos              - Get all todos
   GET  /api/todos/{id}         - Get a specific todo
   POST /api/todos              - Create a new todo
   PUT  /api/todos/{id}         - Update a todo
   DELETE /api/todos/{id}       - Delete a todo
   POST /api/todos/{id}/complete - Mark as completed
   GET  /api/todos/stats/summary - Get statistics

DEVELOPMENT:
   dotnet watch run   # Auto-reload on file changes

BUILDING:
   dotnet build       # Compile the project
   dotnet clean       # Remove build artifacts

DOCUMENTATION:
   Swagger UI: http://localhost:7000/swagger/ui
   Home Page:  http://localhost:7000/
   Health:     http://localhost:7000/health

DATABASE:
   - SQLite database will be created as 'todo.db' in the project root
   - Database is automatically initialized on first run

TROUBLESHOOTING:
   - Port 7000 already in use? Edit appsettings.json or program settings
   - Database issues? Delete todo.db and restart the application
   - Missing dependencies? Run 'dotnet restore'
"""
    }
