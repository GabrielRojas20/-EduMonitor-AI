<?php
/**
 * Seed académico ficticio para la demo masiva de EduMonitor.
 *
 * Ejecutar dentro del contenedor Moodle, después de cargar los CSV:
 *   php /tmp/edumonitor_seed_massive.php
 *
 * El script usa las APIs internas de Moodle y solo trabaja con cursos DEMO-*.
 * No contiene contraseñas, tokens ni datos reales.
 */

if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    exit("Este archivo solo se puede ejecutar por CLI.\n");
}

define('CLI_SCRIPT', true);

$configCandidates = [
    __DIR__ . '/../../config.php',
    '/opt/bitnami/moodle/config.php',
    '/var/www/html/moodle/config.php',
];
$config = null;
foreach ($configCandidates as $candidate) {
    if (is_file($candidate)) {
        $config = $candidate;
        break;
    }
}
if ($config === null) {
    fwrite(STDERR, "No se encontró config.php de Moodle. Ejecuta el script dentro del contenedor Moodle.\n");
    exit(1);
}
require_once($config);
require_once($CFG->libdir . '/clilib.php');
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->dirroot . '/course/modlib.php');
require_once($CFG->dirroot . '/mod/assign/lib.php');
require_once($CFG->libdir . '/gradelib.php');

$now = time();
$createdAssignments = 0;
$createdSubmissions = 0;
$updatedGrades = 0;
$updatedCompletion = 0;

function find_demo_courses(): array {
    global $DB;
    return array_values($DB->get_records_select(
        'course',
        $DB->sql_like('shortname', ':prefix', false),
        ['prefix' => 'DEMO-%'],
        'shortname ASC'
    ));
}

function enrolled_students(int $courseid): array {
    global $DB;
    $sql = "SELECT DISTINCT u.*
              FROM {user} u
              JOIN {user_enrolments} ue ON ue.userid = u.id
              JOIN {enrol} e ON e.id = ue.enrolid
             WHERE e.courseid = :courseid
               AND u.deleted = 0
               AND ue.status = 0
               AND e.status = 0
          ORDER BY u.id";
    $users = $DB->get_records_sql($sql, ['courseid' => $courseid]);
    return array_values(array_filter($users, static function ($user): bool {
        return str_starts_with((string)$user->username, 'estudiante');
    }));
}

function assignment_names(stdClass $course): array {
    $names = [
        'DEMO-01-01' => ['Laboratorio de movimiento', 'Ejercicios de cinemática'], 'DEMO-01-02' => ['Operaciones con matrices', 'Resolución de sistemas lineales'], 'DEMO-01-03' => ['Límites y continuidad', 'Aplicaciones de la derivada'], 'DEMO-01-04' => ['Diagramas de flujo', 'Implementación de algoritmos básicos'], 'DEMO-01-05' => ['Proposiciones y tablas de verdad', 'Demostraciones lógicas'],
        'DEMO-02-01' => ['Ciclo de vida del software', 'Especificación de un sistema'], 'DEMO-02-02' => ['Clases y encapsulamiento', 'Herencia y polimorfismo'], 'DEMO-02-03' => ['Procesos e hilos', 'Gestión de memoria'], 'DEMO-02-04' => ['Planteamiento del problema', 'Diseño del protocolo de investigación'], 'DEMO-02-05' => ['Métodos de interpolación', 'Aproximación de raíces'],
        'DEMO-03-01' => ['Listas y árboles', 'Implementación de grafos'], 'DEMO-03-02' => ['Distribuciones de probabilidad', 'Análisis estadístico de datos'], 'DEMO-03-03' => ['Diagrama de clases', 'Diseño de arquitectura'], 'DEMO-03-04' => ['Modelo OSI y TCP/IP', 'Direccionamiento IPv4'], 'DEMO-03-05' => ['Historias de usuario', 'Planificación de un sprint'],
        'DEMO-04-01' => ['Diseño de red local', 'Configuración de servicios de red'], 'DEMO-04-02' => ['Modelo entidad relación', 'Consultas SQL académicas'], 'DEMO-04-03' => ['Programación lineal', 'Modelo de transporte'], 'DEMO-04-04' => ['Patrones creacionales', 'Patrones estructurales'], 'DEMO-04-05' => ['Plan de pruebas', 'Métricas de calidad'],
        'DEMO-05-01' => ['Levantamiento de requisitos', 'Especificación de requisitos'], 'DEMO-05-02' => ['Arquitectura en capas', 'Evaluación de estilos arquitectónicos'], 'DEMO-05-03' => ['Análisis de vulnerabilidades', 'Controles de seguridad'], 'DEMO-05-04' => ['Maquetación responsive', 'API web y consumo de datos'], 'DEMO-05-05' => ['Cronograma del proyecto', 'Matriz de riesgos'],
    ];
    return $names[$course->shortname] ?? ['Actividad práctica 1', 'Actividad práctica 2'];
}

function get_or_create_assignment(stdClass $course, string $name, int $maxgrade, int $now): array {
    global $DB;
    $module = $DB->get_record('modules', ['name' => 'assign'], '*', MUST_EXIST);
    $existing = $DB->get_record_sql(
        "SELECT a.*, cm.id AS cmid
           FROM {assign} a
           JOIN {course_modules} cm ON cm.instance = a.id AND cm.module = :module
          WHERE a.course = :course AND a.name = :name",
        ['module' => $module->id, 'course' => $course->id, 'name' => $name]
    );
    if ($existing) {
        return [(int)$existing->id, (int)$existing->cmid, false];
    }

    $moduleinfo = (object)[
        'modulename' => 'assign',
        'module' => $module->id,
        'course' => $course->id,
        'section' => 0,
        'name' => $name,
        'intro' => '<p>Actividad ficticia para la demostración de EduMonitor.</p>',
        'introformat' => FORMAT_HTML,
        'grade' => $maxgrade,
        'allowsubmissionsfromdate' => $now,
        'duedate' => $now + 86400,
        'cutoffdate' => 0,
        'gradingduedate' => 0,
        'alwaysshowdescription' => 1,
        'submissiondrafts' => 1,
        'requiresubmissionstatement' => 0,
        'sendnotifications' => 0,
        'sendlatenotifications' => 0,
        'completionsubmit' => 1,
        'completionusegrade' => 1,
        'completion' => COMPLETION_TRACKING_AUTOMATIC,
        'visible' => 1,
        'cmidnumber' => '',
        'groupmode' => 0,
        'groupingid' => 0,
        'availability' => null,
        'tags' => [],
    ];
    $created = add_moduleinfo($moduleinfo, $course);
    $cm = $DB->get_record('course_modules', ['id' => $created->coursemodule], '*', MUST_EXIST);
    return [(int)$created->instance, (int)$cm->id, true];
}

function create_submission(int $assignmentid, int $userid, string $status, int $now): void {
    global $DB;
    $existing = $DB->get_record('assign_submission', [
        'assignment' => $assignmentid,
        'userid' => $userid,
        'attemptnumber' => 0,
    ]);
    if ($existing) {
        return;
    }
    $submissionid = $DB->insert_record('assign_submission', (object)[
        'assignment' => $assignmentid,
        'userid' => $userid,
        'timecreated' => $now,
        'timemodified' => $now,
        'status' => $status,
        'groupid' => 0,
        'attemptnumber' => 0,
        'latest' => 1,
    ]);
    $DB->insert_record('assignsubmission_onlinetext', (object)[
        'assignment' => $assignmentid,
        'submission' => $submissionid,
        'onlinetext' => '<p>Entrega ficticia de demostración.</p>',
        'onlineformat' => FORMAT_HTML,
    ]);
}

function update_grade(int $courseid, int $assignmentid, int $userid, ?float $grade, int $now): void {
    global $DB;
    $grades = [];
    if ($grade !== null) {
        $grades[$userid] = [
            'rawgrade' => $grade,
            'dategraded' => $now,
            'datesubmitted' => $now,
        ];
        grade_update('mod/assign', $courseid, 'mod', 'assign', $assignmentid, 0, $grades);
    }
}

function mark_completion(int $cmid, int $userid, int $state, int $now): void {
    global $DB;
    $existing = $DB->get_record('course_modules_completion', ['coursemoduleid' => $cmid, 'userid' => $userid]);
    if ($existing) {
        $existing->completionstate = $state;
        $existing->timemodified = $now;
        $DB->update_record('course_modules_completion', $existing);
        return;
    }
    $DB->insert_record('course_modules_completion', (object)[
        'coursemoduleid' => $cmid,
        'userid' => $userid,
        'completionstate' => $state,
        'viewed' => 1,
        'timemodified' => $now,
    ]);
}

$courses = find_demo_courses();
if (!$courses) {
    fwrite(STDERR, "No se encontraron cursos DEMO-*. Primero carga cursos-demo-masivo.csv.example.\n");
    exit(1);
}

foreach ($courses as $course) {
    [$activity1, $activity2] = assignment_names($course);
    [$assignment1, $cm1, $created1] = get_or_create_assignment($course, $activity1, 10, $now);
    [$assignment2, $cm2, $created2] = get_or_create_assignment($course, $activity2, 10, $now);
    $createdAssignments += (int)$created1 + (int)$created2;

    $students = enrolled_students((int)$course->id);
    foreach ($students as $index => $student) {
        $n = $index + 1;
        $status1 = $n % 4 === 0 ? 'submitted' : 'submitted';
        $status2 = $n % 4 === 0 ? 'draft' : 'submitted';
        create_submission($assignment1, (int)$student->id, $status1, $now);
        create_submission($assignment2, (int)$student->id, $status2, $now);
        $createdSubmissions += 2;

        $grade1 = $n % 5 === 0 ? 0.0 : (float)(6 + ($n % 5));
        $grade2 = $n % 4 === 0 ? null : (float)(5 + ($n % 6));
        update_grade((int)$course->id, $assignment1, (int)$student->id, $grade1, $now);
        update_grade((int)$course->id, $assignment2, (int)$student->id, $grade2, $now);
        $updatedGrades += $grade2 === null ? 1 : 2;

        mark_completion($cm1, (int)$student->id, $n % 6 === 0 ? COMPLETION_INCOMPLETE : COMPLETION_COMPLETE, $now);
        mark_completion($cm2, (int)$student->id, $n % 4 === 0 ? COMPLETION_INCOMPLETE : COMPLETION_COMPLETE, $now);
        $updatedCompletion += 2;
    }
    rebuild_course_cache($course->id);
}

mtrace("Cursos procesados: " . count($courses));
mtrace("Actividades creadas: $createdAssignments");
mtrace("Entregas nuevas detectadas: $createdSubmissions");
mtrace("Calificaciones procesadas: $updatedGrades");
mtrace("Estados de finalización procesados: $updatedCompletion");
