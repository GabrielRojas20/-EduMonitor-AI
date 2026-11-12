export interface User { id: number; name: string; email?: string; role: 'teacher' | 'admin' }
export interface LoginResponse { accessToken: string; tokenType: 'Bearer'; expiresIn: number; user: User }
export interface Course { id: number; shortName: string; fullName: string; studentCount?: number; lastSyncAt?: string | null }
export type SyncState = 'never' | 'running' | 'succeeded' | 'failed'
export interface SyncStatus { state: SyncState; startedAt?: string | null; finishedAt?: string | null; lastSuccessAt?: string | null; errorCode?: string | null; message?: string | null }
export interface SyncAccepted { syncId: string; state: 'running' }
export type DataStatus = 'available' | 'partial' | 'unavailable'
export interface Metric { value: number | null; unit: 'score_0_10' | 'percent' | 'count'; status: DataStatus; code?: string | null; detail?: string | null; numerator?: number | null; denominator?: number | null }
export interface Counts { gradedCount: number; pendingGradingCount: number; notSubmittedCount: number; draftCount?: number }
export interface Snapshot { snapshotId: string; syncId?: string | null; calculatedAt: string; dataQuality: 'complete' | 'partial' | 'unavailable' }
export interface Analytics { courseId: number; studentId?: number; snapshot: Snapshot; averageScore10: Metric; submissionRate: Metric; gradingRate: Metric; completionRate: Metric; pendingGradingRate: Metric; counts: Counts }
export interface Student { id: number; fullName: string; email?: string }
export interface Paginated<T> { items: T[]; page: number; pageSize: number; total: number }
export type GradeStatus = 'graded' | 'pending_grading' | 'not_submitted'
export type SubmissionStatus = 'none' | 'draft' | 'submitted'
export type CompletionState = 'complete' | 'incomplete' | 'passed' | 'failed' | 'not_available'
export interface Grade { studentId: number; activityId: number; activityName: string; status: GradeStatus; submissionStatus: SubmissionStatus; score?: number | null; maxScore: number; submittedAt?: string | null; gradedAt?: string | null }
export interface ActivityProgress { activityId: number; activityType?: string; completionState: CompletionState }
export interface StudentDetail { student: Student; grades: Grade[]; activities: ActivityProgress[] }
export interface AlertEvidence { metric: string; observedValue?: number | null; threshold?: number | null; numerator?: number | null; denominator?: number | null; sourceIds?: string[]; explanation: string }
export type AlertSeverity = 'info' | 'warning' | 'critical'
export type AlertStatus = 'active' | 'resolved'
export interface AcademicAlert { alertId: string; ruleCode: string; courseId: number; studentId?: number | null; severity: AlertSeverity; status: AlertStatus; detectedAt: string; resolvedAt?: string | null; evidence: AlertEvidence[] }
export interface AgentSource { tool: string; stepN: number }
export interface AgentFact { text: string; sources: AgentSource[] }
export interface AgentInference { text: string; basedOn: number[] }
export interface AgentRecommendation { text: string; relatedFinding?: number | null }
export interface AgentAnswer { facts: AgentFact[]; inferences: AgentInference[]; recommendations: AgentRecommendation[]; unavailable: string[]; message?: string | null }
export interface ChatResponse { traceId: string; answer: AgentAnswer; meta: { courseId?: number | null; lastSyncAt?: string | null; status: 'ok' | 'partial' | 'refused' | 'error' } }
