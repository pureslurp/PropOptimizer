# Error Handling Guide

## Overview
Comprehensive error handling has been implemented throughout the v2 strategy system to ensure the application remains stable and provides helpful feedback when issues occur.

## Error Handling Locations

### 1. Position Filtering (`is_position_appropriate_stat`)

**Location**: Lines 631-696

**Error Scenarios Handled:**
- Missing player data
- Invalid data processor
- Missing attributes in data processor
- Player not found in index
- Exception during position detection

**Behavior:**
- Validates all inputs before processing
- Returns `True` (allow stat) if any validation fails
- Logs warning to console but doesn't crash
- Defaults to permissive behavior when uncertain

**Example Error Message:**
```
Warning: Error in position filtering for Patrick Mahomes - Rushing Yards: 'NoneType' object has no attribute 'get'
```

### 2. Strategy Filtering (`filter_props_by_strategy`)

**Location**: Lines 699-774

**Error Scenarios Handled:**
- Empty or None DataFrame input
- Missing required columns
- Missing streak column when streak filtering requested
- Position filter requested without data processor
- Exception during position filtering
- General filtering errors

**Behavior:**
- Validates DataFrame and columns before filtering
- Logs warnings for missing data
- Returns empty DataFrame on error (safe fallback)
- Continues processing even if position filtering fails

**Example Error Messages:**
```
Warning: Missing required columns: ['total_score']
Warning: Streak filter requested but 'streak' column not found
Warning: Position filter requested but no data_processor provided
Error in filter_props_by_strategy: division by zero
```

### 3. Display Function (`display_prop_picks`)

**Location**: Lines 1627-1726

**Error Scenarios Handled:**
- Filter function exceptions
- Empty results from filtering

**Behavior:**
- Wraps filter call in try-except
- Shows error in Streamlit UI if filtering fails
- Displays informative message when no props match criteria
- Includes criteria details in "no results" message
- Provides helpful suggestions

**Example UI Messages:**
```
❌ Error filtering props: column 'streak' not found

*No props meet the criteria: Score 80+ | Odds -300 to -150 | Streak 3+ | Position-appropriate only*
💡 Try adjusting filters or check back when more games are available
```

### 4. ROI Calculation (`calculate_all_strategies_roi`)

**Location**: Lines 777-868

**Error Scenarios Handled:**
- Strategy-level calculation errors
- Week-level calculation errors
- Missing data for specific weeks
- Data processor initialization failures

**Behavior:**
- Each strategy wrapped in try-except
- Each week wrapped in try-except
- Continues processing other strategies/weeks on error
- Returns 0.0 ROI for failed strategies
- Logs warnings with strategy and week details

**Example Error Messages:**
```
Warning: Error calculating ROI for v2_Optimal week 4: props_df is empty
Warning: Error calculating ROI for v2_Greasy: division by zero
```

### 5. ROI Table Display

**Location**: Lines 1793-1882

**Error Scenarios Handled:**
- Missing ROI data
- Invalid numeric values
- Table rendering errors
- Data extraction errors

**Behavior:**
- Safe extraction with `.get()` and defaults
- Format function handles exceptions
- Entire table wrapped in try-except
- Shows user-friendly error in UI
- Returns "N/A" for invalid values

**Example UI Messages:**
```
❌ Error displaying ROI table: 'NoneType' object has no attribute 'get'
ℹ️ ROI data could not be displayed. Please check console for details.

ℹ️ Not enough historical data to calculate ROI (requires weeks 4+)
```

## Error Handling Principles

### 1. **Fail Gracefully**
- Never crash the entire application
- Return safe defaults (empty DataFrame, 0.0, True)
- Continue processing when partial failure occurs

### 2. **Informative Messages**
- Console warnings include context (player name, week, strategy)
- UI messages are user-friendly and actionable
- Include relevant criteria when showing "no results"

### 3. **Defensive Programming**
- Validate inputs before processing
- Check for required attributes/columns
- Use `.get()` with defaults for dictionaries
- Handle None/empty cases explicitly

### 4. **Logging Strategy**
- `print()` to console for debugging (shown in terminal)
- `st.error()` for critical UI errors
- `st.warning()` for non-critical issues
- `st.info()` for helpful guidance

## Common Error Scenarios

### No Props Match Criteria

**Cause**: Filters too strict for available data

**User Sees:**
```
*No props meet the criteria: Score 80+ | Odds -300 to -150 | Streak 3+ | Position-appropriate only*
💡 Try adjusting filters or check back when more games are available
```

**Resolution**: User can adjust filters in sidebar or wait for more games

### Missing Historical Data

**Cause**: Week doesn't have box score or props data

**User Sees:**
```
ℹ️ Not enough historical data to calculate ROI (requires weeks 4+)
```

**Resolution**: ROI calculation requires at least week 4 data; earlier weeks are skipped

### Position Filter Error

**Cause**: Data processor missing player data

**Console Shows:**
```
Warning: Error in position filtering for Unknown Player - Passing Yards: KeyError
```

**User Impact**: None - stat is allowed by default

**Resolution**: Automatic - position filtering degrades gracefully

### Data Processor Not Available

**Cause**: Historical mode or data loading issue

**Console Shows:**
```
Warning: Position filter requested but no data_processor provided
```

**User Impact**: Position filtering skipped for that query

**Resolution**: Automatic - continues without position filtering

## Testing Error Handling

### Test Empty Results
```python
# In Streamlit app, set very strict filters:
# - Score: 95+
# - Odds: -180 to -150
# - Streak: 10+
# Should show "No props meet the criteria" message
```

### Test Missing Data
```python
# Remove a week's box_score_debug.csv file
# ROI calculation should skip that week with warning
```

### Test Position Filter Edge Cases
```python
# Create props for players not in data processor
# Should default to allowing the stat
```

## Future Improvements

1. **Structured Logging**: Replace print() with proper logging module
2. **Error Reporting**: Track error frequency and patterns
3. **User Notifications**: Add option to suppress certain warnings
4. **Retry Logic**: Automatically retry failed data loads
5. **Validation Rules**: Define explicit validation schemas
6. **Error Categories**: Classify errors by severity (INFO, WARNING, ERROR, CRITICAL)

## Debug Mode

To see all error messages, run the app with:
```bash
streamlit run player_prop_optimizer.py 2>&1 | tee debug.log
```

This will log all console output to both screen and `debug.log` file.

## Support

If you encounter errors:

1. **Check Console Output**: Look for "Warning" or "Error" messages
2. **Check Criteria**: Verify filters aren't too strict
3. **Check Data Availability**: Ensure week has required data files
4. **Clear Cache**: Click "Refresh" button to reload data
5. **Restart App**: Stop and restart Streamlit if issues persist

## Error Handling Checklist

When adding new features:

- [ ] Validate all inputs
- [ ] Handle None/empty cases
- [ ] Use try-except around risky operations
- [ ] Return safe defaults on error
- [ ] Log errors with context
- [ ] Show user-friendly messages
- [ ] Test with missing/invalid data
- [ ] Document error scenarios

## Summary

The error handling system ensures:
- ✅ Application never crashes from data issues
- ✅ Users see helpful messages
- ✅ Debugging information available in console
- ✅ Graceful degradation when features unavailable
- ✅ Continues processing even when partial failures occur

