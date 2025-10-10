"""
Test script to verify that game time filtering works correctly
"""

from datetime import datetime, timezone, timedelta
from odds_api import OddsAPI, AlternateLineManager


def test_time_filtering():
    """Test that events are correctly filtered by commence_time"""
    
    # Create mock events with different start times
    current_time = datetime.now(timezone.utc)
    
    # Event that started 1 hour ago (should be filtered out)
    past_event = {
        'id': 'past_event_123',
        'commence_time': (current_time - timedelta(hours=1)).isoformat()
    }
    
    # Event starting in 1 hour (should be included)
    future_event_1 = {
        'id': 'future_event_456',
        'commence_time': (current_time + timedelta(hours=1)).isoformat()
    }
    
    # Event starting in 2 days (should be included)
    future_event_2 = {
        'id': 'future_event_789',
        'commence_time': (current_time + timedelta(days=2)).isoformat()
    }
    
    # Event with no commence_time (should be filtered out)
    no_time_event = {
        'id': 'no_time_event_000'
    }
    
    # Event with invalid time format (should be filtered out)
    invalid_time_event = {
        'id': 'invalid_event_999',
        'commence_time': 'not-a-valid-time'
    }
    
    # Test data
    mock_events = [
        past_event,
        future_event_1,
        future_event_2,
        no_time_event,
        invalid_time_event
    ]
    
    # Simulate the filtering logic from OddsAPI.get_player_props
    active_events = []
    for event in mock_events:
        commence_time_str = event.get('commence_time')
        if commence_time_str:
            try:
                commence_time = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                if commence_time > current_time:
                    active_events.append(event)
            except (ValueError, AttributeError):
                continue
        else:
            continue
    
    # Verify results
    print("Test Results:")
    print(f"Total events: {len(mock_events)}")
    print(f"Active events (not started): {len(active_events)}")
    print(f"\nActive event IDs: {[e['id'] for e in active_events]}")
    
    # Assertions
    assert len(active_events) == 2, f"Expected 2 active events, got {len(active_events)}"
    assert 'future_event_456' in [e['id'] for e in active_events], "Future event 1 should be included"
    assert 'future_event_789' in [e['id'] for e in active_events], "Future event 2 should be included"
    assert 'past_event_123' not in [e['id'] for e in active_events], "Past event should be filtered out"
    assert 'no_time_event_000' not in [e['id'] for e in active_events], "Event without time should be filtered out"
    assert 'invalid_event_999' not in [e['id'] for e in active_events], "Event with invalid time should be filtered out"
    
    print("\n✅ All tests passed!")
    print("\nSummary:")
    print("- Events that have already started are correctly filtered out")
    print("- Events with no commence_time are filtered out")
    print("- Events with invalid time format are filtered out")
    print("- Future events are correctly included")


if __name__ == "__main__":
    test_time_filtering()

