using Microsoft.EntityFrameworkCore;

namespace AuthCourses.Api;

public class AuthDb(DbContextOptions<AuthDb> options) : DbContext(options)
{
    public DbSet<AppUser> Users => Set<AppUser>();
    public DbSet<CourseEntity> Courses => Set<CourseEntity>();
    public DbSet<TeacherCourse> TeacherCourses => Set<TeacherCourse>();

    protected override void OnModelCreating(ModelBuilder b)
    {
        b.HasDefaultSchema("auth");

        b.Entity<AppUser>(e =>
        {
            e.ToTable("Users");
            e.HasKey(x => x.Id);
            e.HasIndex(x => x.Email).IsUnique();
            e.Property(x => x.Email).HasMaxLength(256);
            e.Property(x => x.Name).HasMaxLength(200);
            e.Property(x => x.Role).HasMaxLength(20);
            e.Property(x => x.PasswordHash).HasMaxLength(500);
        });

        b.Entity<CourseEntity>(e =>
        {
            e.ToTable("Courses");
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).ValueGeneratedNever();
            e.Property(x => x.ShortName).HasMaxLength(100);
            e.Property(x => x.FullName).HasMaxLength(300);
        });

        b.Entity<TeacherCourse>(e =>
        {
            e.ToTable("TeacherCourses");
            e.HasKey(x => new { x.UserId, x.CourseId });
        });
    }
}

// Datos de prueba ficticios. La contraseña viene de AUTH_SEED_PASSWORD (nunca del código).
public static class Seed
{
    public static void Run(AuthDb db, PasswordService passwords, string password, string dataset = "minimal")
    {
        if (db.Users.Any()) return;

        if (string.Equals(dataset, "massive", StringComparison.OrdinalIgnoreCase))
        {
            RunMassive(db, passwords, password);
            return;
        }

        if (!db.Courses.Any())
        {
            db.Courses.AddRange(
                new CourseEntity { Id = 2, ShortName = "PRUEBA01", FullName = "Curso de Prueba EduMonitor" },
                new CourseEntity { Id = 3, ShortName = "PRUEBA02", FullName = "Curso de Prueba 2" });
        }

        var docente1 = new AppUser { Email = "docente1@edumonitor.test", Name = "Docente Uno", Role = "teacher", PasswordHash = passwords.Hash(password) };
        var docente2 = new AppUser { Email = "docente2@edumonitor.test", Name = "Docente Dos", Role = "teacher", PasswordHash = passwords.Hash(password) };
        var admin = new AppUser { Email = "admin@edumonitor.test", Name = "Administrador Técnico", Role = "admin", PasswordHash = passwords.Hash(password) };
        db.Users.AddRange(docente1, docente2, admin);
        db.SaveChanges();

        // Docente 1 -> curso 2 (PRUEBA01, el de Moodle). Docente 2 -> curso 3. El administrador no tiene cursos.
        db.TeacherCourses.AddRange(
            new TeacherCourse { UserId = docente1.Id, CourseId = 2 },
            new TeacherCourse { UserId = docente2.Id, CourseId = 3 });
        db.SaveChanges();
    }

    private static void RunMassive(AuthDb db, PasswordService passwords, string password)
    {
        var courses = Enumerable.Range(0, 25)
            .Select(i => new CourseEntity
            {
                Id = 201 + i,
                ShortName = $"DEMO-{i / 5 + 1:00}-{i % 5 + 1:00}",
                FullName = $"Curso demo {i / 5 + 1}, grupo {i % 5 + 1}"
            })
            .ToArray();
        db.Courses.AddRange(courses);

        var teachers = Enumerable.Range(1, 5)
            .Select(i => new AppUser
            {
                Email = $"docente{i}@edumonitor.test",
                Name = $"Docente Demo {i}",
                Role = "teacher",
                PasswordHash = passwords.Hash(password)
            })
            .ToArray();
        var admin = new AppUser
        {
            Email = "admin@edumonitor.test",
            Name = "Administrador Técnico",
            Role = "admin",
            PasswordHash = passwords.Hash(password)
        };
        db.Users.AddRange(teachers);
        db.Users.Add(admin);
        db.SaveChanges();

        var links = new List<TeacherCourse>();
        for (var teacher = 0; teacher < teachers.Length; teacher++)
        {
            for (var course = 0; course < 5; course++)
            {
                links.Add(new TeacherCourse
                {
                    UserId = teachers[teacher].Id,
                    CourseId = courses[teacher * 5 + course].Id
                });
            }
        }
        db.TeacherCourses.AddRange(links);
        db.SaveChanges();
    }
}
