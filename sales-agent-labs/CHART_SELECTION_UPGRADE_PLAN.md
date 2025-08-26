# Chart Selection Intelligence Upgrade Plan
**Created**: August 25, 2025  
**Status**: Planning Phase - Ready for Implementation

## Executive Summary

This document outlines a comprehensive 3-phase upgrade to the PresGen chart selection system, transforming it from a basic data-driven approach to an intelligent intent-aware system with contextual bullet summaries. The upgrade will significantly improve user experience by matching chart types to user questions and providing explanatory bullet points for each visualization.

## Current System Analysis

### Existing Chart Selection Logic (`src/mcp/tools/data.py:208-249`)
The current system uses a **data-structure-driven approach**:
- Analyzes resulting DataFrame (columns, rows, data types)
- Maps data patterns to 5 chart types: `single_value_bar`, `single_col_bar`, `line`, `bar`, `table`
- Prioritizes reliability over sophistication

### Limitations Identified
- **No user intent consideration**: "Sales trends over time" → bar chart instead of line chart
- **Limited chart variety**: Only 5 basic chart types available
- **No explanatory context**: Charts lack bullet summaries to explain insights
- **Pattern-only selection**: Missing sophisticated relationship analysis

## 3-Phase Upgrade Strategy

### Phase 1: Enhanced Pattern Matching + Basic Bullet Summaries
**Timeline**: 3-4 days | **Risk**: Low | **Immediate Impact**: High

#### Key Changes
1. **Intent Pattern Recognition**
   - Add regex patterns for: temporal, comparison, ranking, distribution, composition
   - Location: `src/mcp/tools/data.py` (new `VISUALIZATION_INTENT_PATTERNS` dict)

2. **Basic Bullet Generation**
   - Pattern-based bullet generation for each intent type
   - Location: New functions `_generate_chart_bullets()`, `_generate_temporal_bullets()`, etc.

3. **Enhanced Chart Selection**
   - Modify `_choose_chart()` to accept `question` parameter
   - Intent-aware selection with data validation fallback

4. **Slides Integration**
   - Update `src/agent/slides_google.py` to include bullet points in slide layouts
   - Two-column layout: bullets left, chart right

#### Implementation Steps
```python
# Step 1: Add intent patterns
VISUALIZATION_INTENT_PATTERNS = {
    'temporal': [r'\bover\s+time\b', r'\btrend(?:s|ing)?\b'],
    'ranking': [r'\btop\s+\d+\b', r'\bbest\b', r'\bworst\b'],
    # ... etc
}

# Step 2: Intent classification function
def _classify_question_intent(question: str) -> str:
    # Pattern matching logic
    
# Step 3: Enhanced chart selection
async def _choose_chart(df, question="", sql_query="") -> str:
    intent = _classify_question_intent(question)
    # Intent-aware selection with fallback
```

### Phase 2: LLM Intent Classification + Enhanced Bullet Summaries  
**Timeline**: 4-5 days | **Risk**: Medium | **Advanced Intelligence**

#### Key Enhancements
1. **Hybrid Intent Classification**
   - Pattern matching first (fast, reliable)
   - Gemini 2.0 Flash fallback for complex questions
   - Location: New `_classify_intent_with_llm()` function

2. **LLM-Powered Bullet Generation**
   - Context-aware bullet generation using Gemini
   - Business-friendly language with specific insights
   - Fallback to pattern-based bullets on failure

3. **Async Architecture**
   - Convert chart selection pipeline to async
   - Proper timeout handling for LLM calls

#### Implementation Strategy
```python
# Hybrid classification
async def _classify_question_intent_hybrid(question: str) -> str:
    # Try patterns first
    pattern_intent = _classify_question_intent_patterns(question)
    if pattern_intent != 'general':
        return pattern_intent
    
    # Fallback to LLM
    return await _classify_intent_with_llm(question)

# LLM bullet generation  
async def _generate_chart_bullets_with_llm(df, chart_type, question, intent, sql_query) -> list:
    # Prepare data summary for LLM
    # Generate contextual business insights
    # Parse and validate bullet points
```

### Phase 3: Expanded Chart Types + Specialized Bullet Summaries
**Timeline**: 5-6 days | **Risk**: Medium-High | **Full Feature Set**

#### New Chart Types Added
- **scatter**: Relationship analysis with correlation detection
- **histogram**: Distribution analysis with statistical insights  
- **pie**: Composition with percentage breakdowns
- **stacked_bar**: Multi-dimensional composition
- **horizontal_bar**: Better for long category labels
- **area**: Time series with emphasis on cumulative values
- **box_plot**: Statistical distribution analysis

#### Chart-Type-Specific Features
```python
CHART_TYPE_BULLET_GENERATORS = {
    'scatter': _generate_scatter_bullets,  # Correlation insights
    'pie': _generate_pie_bullets,          # Percentage analysis
    'histogram': _generate_histogram_bullets, # Statistical summary
    # ... etc
}

# Example: Scatter plot bullets
def _generate_scatter_bullets(df, question, **kwargs) -> list:
    # Calculate correlation coefficient
    # Identify outliers using IQR method
    # Provide range and relationship insights
```

#### Advanced Features
1. **Chart Requirement Validation**
   - Validate data meets requirements for selected chart type
   - Graceful fallback to simpler chart types

2. **Visual Context Integration**
   - Add visual references to bullet points
   - "Strong upward trend (see line slope)", "Largest segment (biggest slice)"

3. **Smart Chart Selection**
   - Multi-candidate evaluation with ranking
   - Complexity management via configuration

## Integration Architecture

### Enhanced Data Flow
```
User Question → Intent Classification → SQL Generation → Data Analysis → 
Chart Type Selection → Chart Rendering → Bullet Generation → Slide Creation
```

### Updated Return Structure
```python
return {
    "sql": sql,
    "chart_path": chart_path,
    "chart_type": chart_type,
    "bullet_points": bullet_points,        # NEW: Explanatory bullets
    "chart_intent": intent,                # NEW: Classified intent
    "insights": _generate_insights(df, question, sql),
    "row_count": len(df),
    "generation_method": {                 # NEW: Monitoring metadata
        "bullet_method": "advanced|hybrid|pattern",
        "used_llm_for_bullets": bool,
        "chart_complexity": "low|medium|high"
    }
}
```

### Slides Integration Updates
- **Two-column slide layout**: Bullets left, chart right
- **Consistent formatting**: Business-friendly bullet points
- **Visual context**: References to chart elements in bullets

## Implementation Roadmap

### Week 1-2: Phase 1 Implementation
- [ ] Add intent pattern dictionary
- [ ] Implement basic bullet generation functions
- [ ] Update chart selection with intent awareness
- [ ] Modify slides integration for bullet display
- [ ] Create comprehensive unit tests
- [ ] Deploy with feature flag (`CHART_SELECTION_VERSION=v2`)

### Week 3-4: Phase 2 Implementation  
- [ ] Implement LLM intent classification
- [ ] Add LLM-powered bullet generation
- [ ] Convert to async architecture
- [ ] Add configuration management
- [ ] Performance testing and optimization
- [ ] Monitor LLM usage and costs

### Week 5-7: Phase 3 Implementation
- [ ] Add new chart type rendering functions
- [ ] Implement chart-specific bullet generators
- [ ] Add chart requirement validation
- [ ] Create visual context integration
- [ ] Comprehensive testing of all chart types
- [ ] Full deployment (`CHART_SELECTION_VERSION=v3`)

### Week 8: Monitoring and Optimization
- [ ] Performance analysis and optimization
- [ ] User feedback collection and analysis  
- [ ] Documentation updates
- [ ] Production monitoring setup

## Risk Management

### Backward Compatibility Strategy
```python
# Feature flagging for safe rollout
CHART_SELECTION_VERSION = "v2"  # v1 (legacy), v2 (hybrid), v3 (full)

async def _choose_chart_with_fallback(df, question="", sql_query=""):
    try:
        if CHART_SELECTION_VERSION == "v1":
            return _choose_chart_legacy(df)
        # ... version-specific logic
    except Exception as e:
        logger.error(f"Advanced chart selection failed: {e}")
        return _choose_chart_legacy(df)  # Always fallback to working system
```

### Performance Safeguards
- **Timeout Management**: LLM calls limited to 10 seconds for intent, 15 seconds for bullets
- **Fallback Strategy**: Pattern-based bullets when LLM fails
- **Caching**: Intent classification results cached by question hash
- **Monitoring**: Track success rates, performance metrics, LLM usage

### Quality Assurance
- **Visual Regression Testing**: Generate reference charts for comparison
- **A/B Testing**: Compare chart selection accuracy between versions
- **User Feedback Loop**: Monitor slide quality and user satisfaction

## Configuration Management

### Updated `config.yaml`
```yaml
data_tool:
  chart_selection:
    version: "v2"  # v1, v2, v3
    enable_llm_fallback: true
    enable_new_chart_types: false  # Phase 3
    
  bullet_generation:
    use_llm_enhancement: true
    llm_fallback_timeout: 10  # seconds
    max_bullets_per_chart: 4
    business_language: true
    
  monitoring:
    track_intent_classification: true
    track_chart_selection_accuracy: true
    log_bullet_generation_method: true
```

## Success Metrics

### Quantitative Metrics
- **Intent Classification Accuracy**: >85% correct intent detection
- **Chart Selection Relevance**: >90% appropriate chart type for intent
- **Bullet Generation Quality**: >80% bullets rated as "helpful" 
- **Performance Impact**: <20% increase in total processing time
- **System Reliability**: <5% increase in error rate

### Qualitative Metrics  
- **User Satisfaction**: Slide explanations are clear and actionable
- **Business Value**: Charts provide immediate insights without additional explanation
- **Visual Appeal**: Professional presentation quality maintained
- **Usability**: Bullet points enhance rather than clutter slide content

## Dependencies and Requirements

### Code Dependencies
```python
# New requirements.txt additions
seaborn>=0.12.0      # Advanced statistical plots
plotly>=5.17.0       # Interactive charts (future use)
scipy>=1.11.0        # Statistical analysis for bullet generation
```

### Infrastructure Requirements
- **LLM API Quotas**: Increased Gemini usage for intent classification and bullet generation
- **Storage**: Additional space for new chart types and caching
- **Monitoring**: Enhanced logging for intent classification and bullet generation methods

## Testing Strategy

### Unit Testing
```python
# tests/test_chart_intent.py
def test_temporal_pattern_detection():
    assert _classify_question_intent("Sales over time") == "temporal"
    
def test_scatter_bullet_generation():
    # Test correlation detection in bullet generation
    
def test_chart_requirement_validation():
    # Test data requirements for each chart type
```

### Integration Testing
- **End-to-end pipeline testing** with real data files
- **LLM integration testing** with timeout scenarios  
- **Slide creation testing** with bullet point layouts
- **Performance testing** with complex datasets

### Visual Testing
- **Chart rendering verification** for all new chart types
- **Bullet point formatting** validation in slide layouts
- **Cross-browser compatibility** for generated presentations

## Future Enhancement Opportunities

### Short-term Enhancements (Post-Phase 3)
- **Interactive Charts**: Plotly integration for web-based presentations
- **Template-based Bullets**: Industry-specific bullet point templates
- **Multi-language Support**: Bullet generation in different languages

### Long-term Vision
- **AI-Powered Design**: Automatic color scheme and layout optimization
- **Real-time Collaboration**: Live editing of bullet points and chart selections
- **Advanced Analytics**: Presentation engagement tracking and optimization

---

## Conclusion

This comprehensive upgrade plan transforms the PresGen chart selection system from a basic data-driven approach to an intelligent, intent-aware system that provides both appropriate visualizations and contextual explanations. The phased approach ensures minimal risk while delivering significant value to users through better chart selection and clear, actionable bullet summaries.

The plan maintains backward compatibility while introducing sophisticated AI capabilities that enhance the user experience without compromising system reliability. Upon completion, users will receive presentations with charts that truly match their questions and bullet points that immediately communicate the key insights.

**Next Steps**: Begin Phase 1 implementation with intent pattern matching and basic bullet generation, targeting completion within 2 weeks for immediate user impact.