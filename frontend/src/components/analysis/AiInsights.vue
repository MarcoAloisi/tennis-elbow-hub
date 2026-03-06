<script setup lang="ts">
import { ref, computed } from 'vue'
import { Bot, Sparkles, RefreshCw, AlertCircle, Target, AlertTriangle, Lightbulb, CheckCircle, FileText } from 'lucide-vue-next'
import { apiUrl } from '@/config/api'
import { useAnalysisStore } from '@/stores/analysis'

const store = useAnalysisStore()

const isLoading = ref(false)
const analysis = ref<any>(null)
const errorMsg = ref('')
const hasAnalyzed = ref(false)

async function requestAnalysis() {
  isLoading.value = true
  errorMsg.value = ''

  try {
    const match = store.currentMatch
    if (!match) {
      errorMsg.value = 'No match selected'
      return
    }

    const userName = store.mainPlayerName || match.player1?.name || 'Player'

    const payload = {
      info: match.info,
      player1: match.player1,
      player2: match.player2,
      userName
    }

    const response = await fetch(apiUrl('/api/analysis/ai-insights'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    const data = await response.json()

    if (data.success) {
      try {
        // Strip out any markdown code blocks the LLM might have incorrectly wrapped it in
        let jsonStr = data.analysis.trim()
        if (jsonStr.startsWith('```json')) {
          jsonStr = jsonStr.substring(7)
        }
        if (jsonStr.startsWith('```')) {
          jsonStr = jsonStr.substring(3)
        }
        if (jsonStr.endsWith('```')) {
          jsonStr = jsonStr.substring(0, jsonStr.length - 3)
        }
        
        analysis.value = JSON.parse(jsonStr.trim())
        hasAnalyzed.value = true
      } catch (err) {
        console.error("Failed to parse JSON:", data.analysis, err)
        errorMsg.value = 'Failed to interpret AI response. Please try again.'
      }
    } else {
      errorMsg.value = data.error || 'Analysis failed'
    }
  } catch (e: any) {
    errorMsg.value = e.message || 'Network error. Please try again.'
  } finally {
    isLoading.value = false
  }
}

// Kept formatContent but simplified since sections are now handled natively

function formatContent(text: string): string {
  return text
    // Remove isolated ** on their own lines (which AI sometimes outputs to wrap sections)
    .replace(/^\s*\*\*\s*$/gm, '')
    // Remove stray ** at the very start or end of the text block
    .replace(/^\s*\*\*\s*/g, '')
    .replace(/\s*\*\*\s*$/g, '')
    // Bold: **text** (supports multi-line)
    .replace(/\*\*([\s\S]+?)\*\*/g, '<strong>$1</strong>')
    // Bullet list items: - text or * text or • text
    .replace(/^[-*•]\s+(.+)$/gm, '<div class="ai-bullet-item"><span class="ai-bullet-dot"></span><span class="ai-bullet-text">$1</span></div>')
    // Numbered list items: 1. text
    .replace(/^(\d+)\.\s+(.+)$/gm, '<div class="ai-bullet-item"><span class="ai-num">$1.</span><span class="ai-bullet-text">$2</span></div>')
    // Paragraphs (double newlines)
    .replace(/\n\n/g, '</p><p>')
    // Single newlines (not inside bullet items)
    .replace(/\n/g, '<br>')
}
</script>

<template>
  <div class="ai-section">
    <!-- Initial state -->
    <div v-if="!hasAnalyzed && !isLoading" class="ai-prompt-card">
      <div class="ai-icon-wrapper">
        <Bot :size="40" stroke-width="1.5" />
      </div>
      <h3>AI Match Coach</h3>
      <p>Get personalized coaching insights for this match. Our AI will analyze your performance and provide actionable feedback.</p>
      <button class="ai-analyze-btn" @click="requestAnalysis" :disabled="isLoading">
        <Sparkles :size="18" />
        Get AI Analysis
      </button>
      <div v-if="errorMsg" class="ai-error">
        <AlertCircle :size="16" />
        {{ errorMsg }}
        <button class="retry-link" @click="requestAnalysis">Try Again</button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="ai-loading-card">
      <div class="ai-spinner"></div>
      <p class="loading-text">Analyzing your match...</p>
      <p class="loading-sub">This may take a moment</p>
    </div>

    <!-- Analysis result -->
    <div v-if="hasAnalyzed && !isLoading" class="ai-result-card">
      <div class="ai-result-header">
        <div class="ai-result-title">
          <Bot :size="22" />
          <h3>AI Coach Analysis</h3>
        </div>
        <button class="btn btn-ghost btn-sm" @click="requestAnalysis" title="Re-analyze">
          <RefreshCw :size="16" />
        </button>
      </div>

      <div v-if="analysis" class="ai-sections">
        
        <!-- Match Summary -->
        <div v-if="analysis.match_summary" class="ai-section-card" style="--section-color: var(--color-accent)">
          <div class="section-header">
            <FileText :size="18" class="section-icon" />
            <h4>Match Summary</h4>
          </div>
          <div class="section-body" v-html="formatContent(analysis.match_summary)"></div>
        </div>

        <!-- Strengths -->
        <div v-if="analysis.strengths?.length" class="ai-section-card" style="--section-color: var(--color-success)">
          <div class="section-header">
            <Target :size="18" class="section-icon" />
            <h4>Strengths</h4>
          </div>
          <div class="section-body">
            <div v-for="(item, idx) in analysis.strengths" :key="idx" class="ai-bullet-item mb-2">
              <span class="ai-bullet-dot"></span>
              <span class="ai-bullet-text">
                <strong style="color: var(--color-text-primary);">{{ item.title }}</strong>: <span v-html="formatContent(item.explanation)"></span>
              </span>
            </div>
          </div>
        </div>

        <!-- Areas for Improvement -->
        <div v-if="analysis.areas_for_improvement?.length" class="ai-section-card" style="--section-color: var(--color-warning)">
          <div class="section-header">
            <AlertTriangle :size="18" class="section-icon" />
            <h4>Areas for Improvement</h4>
          </div>
          <div class="section-body">
            <div v-for="(item, idx) in analysis.areas_for_improvement" :key="idx" class="ai-bullet-item mb-2">
              <span class="ai-bullet-dot"></span>
              <span class="ai-bullet-text">
                <strong style="color: var(--color-text-primary);">{{ item.title }}</strong>: <span v-html="formatContent(item.explanation)"></span>
              </span>
            </div>
          </div>
        </div>

        <!-- Tactical Insights -->
        <div v-if="analysis.tactical_insights?.length" class="ai-section-card" style="--section-color: var(--color-accent)">
          <div class="section-header">
            <Lightbulb :size="18" class="section-icon" />
            <h4>Tactical Insights</h4>
          </div>
          <div class="section-body">
            <div v-for="(item, idx) in analysis.tactical_insights" :key="idx" class="ai-bullet-item mb-2">
              <span class="ai-bullet-dot"></span>
              <span class="ai-bullet-text">
                <strong style="color: var(--color-text-primary);">{{ item.title }}</strong>: <span v-html="formatContent(item.explanation)"></span>
              </span>
            </div>
          </div>
        </div>

        <!-- Key Takeaways -->
        <div v-if="analysis.key_takeaways?.length" class="ai-section-card" style="--section-color: var(--color-success)">
          <div class="section-header">
            <CheckCircle :size="18" class="section-icon" />
            <h4>Key Takeaways</h4>
          </div>
          <div class="section-body">
            <div v-for="(item, idx) in analysis.key_takeaways" :key="idx" class="ai-bullet-item mb-2">
              <span class="ai-bullet-dot"></span>
              <span class="ai-bullet-text" v-html="formatContent(item)"></span>
            </div>
          </div>
        </div>

      </div>

      <div v-if="errorMsg" class="ai-error" style="padding: var(--space-4) var(--space-6);">
        <AlertCircle :size="16" />
        {{ errorMsg }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-section {
  margin-top: var(--space-4);
}

.ai-prompt-card {
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, rgba(59, 177, 67, 0.08) 100%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
}

.ai-icon-wrapper {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-accent);
}

.ai-prompt-card h3 {
  margin: 0;
  font-size: var(--font-size-lg);
}

.ai-prompt-card p {
  color: var(--color-text-secondary);
  max-width: 450px;
  margin: 0;
  font-size: var(--font-size-sm);
}

.ai-analyze-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  background: var(--color-accent);
  color: var(--color-text-inverse);
  border-radius: var(--radius-full);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-sm);
  transition: all var(--transition-fast);
  cursor: pointer;
  margin-top: var(--space-2);
}

.ai-analyze-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 177, 67, 0.3);
}

.ai-analyze-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Loading */
.ai-loading-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-10);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
}

.ai-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-weight: var(--font-weight-medium);
  margin: 0;
}

.loading-sub {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin: 0;
}

/* Result */
.ai-result-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.ai-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-6);
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
}

.ai-result-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-accent);
}

.ai-result-title h3 {
  margin: 0;
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
}

/* Sections */
.ai-sections {
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.ai-section-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--section-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.section-icon {
  color: var(--section-color);
  flex-shrink: 0;
}

.section-header h4 {
  margin: 0;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.section-body {
  padding: var(--space-4);
  font-size: var(--font-size-sm);
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.section-body :deep(strong) {
  color: var(--color-text-primary);
}

.section-body :deep(p) {
  margin: var(--space-1) 0;
}

.section-body :deep(.ai-bullet-item) {
  display: flex;
  gap: var(--space-2);
  margin: var(--space-2) 0;
  align-items: flex-start;
}

.section-body :deep(.ai-bullet-dot) {
  width: 6px;
  height: 6px;
  min-width: 6px;
  border-radius: 50%;
  background: var(--section-color);
  margin-top: 8px;
}

.section-body :deep(.ai-num) {
  color: var(--section-color);
  font-weight: var(--font-weight-bold);
  min-width: 20px;
}

.section-body :deep(.ai-bullet-text) {
  flex: 1;
}

/* Error */
.ai-error {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-danger);
  font-size: var(--font-size-sm);
  margin-top: var(--space-3);
}

.retry-link {
  color: var(--color-accent);
  text-decoration: underline;
  cursor: pointer;
  background: none;
  border: none;
  font-size: var(--font-size-sm);
}
</style>
