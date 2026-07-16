from datetime import datetime, timezone
import io
from unittest.mock import patch, MagicMock


# =============================================
# TEST THE STANDALONE FUNCTIONS FROM DSOC_SIM
# =============================================


# ==============================================================================
# IMPORTANT:
# Because we read "ngrok_endpoint.env" on import, we need to patch the Path globally
# before importing all the functions we want to test.
# ==============================================================================
mock_env_data = "BOOTSTRAP_SERVER=localhost:9092\nSOME_OTHER_VAR=value\nWEED_S3_DOMAIN=seaweedfs.fake.com\nWEED_S3_ACCESS_KEY=fake_access_key\nWEED_S3_SECRET_KEY=fake_key\nWEED_S3_BUCKET=fake_bucket" 
with patch("pathlib.Path.read_text", return_value=mock_env_data):
    from ngRadar_Website.management.commands.dsoc_sim import (
        Command,
        DB_import,
        DB_columns,
        publish_DB,
        create_img,
        save_image_to_seaweedfs,
        consume,
    )

    

# ==============================================================================
# 1. DB_import Test
# ==============================================================================

@patch("ngRadar_Website.management.commands.dsoc_sim.gbtEvent")
def test_db_import_success(mock_gbt_event):
    """Scenario 1: Successfully retrieve and format data matching a UUID."""
    mock_record = ("obj_123", "Mars", "SineWave", datetime(2026, 1, 1, tzinfo=timezone.utc))
    
    # Mocking Django chain query syntax: .filter().values_list().first()
    mock_query = mock_gbt_event.objects.filter.return_value
    mock_values = mock_query.values_list.return_value
    mock_values.first.return_value = mock_record

    result = DB_import("9c85a7c7-0506-44f3-9792-63b1867c6f97") # random uuid I pulled from render DB to test with
    
    assert result == mock_record
    mock_gbt_event.objects.filter.assert_called_once_with(uuid="9c85a7c7-0506-44f3-9792-63b1867c6f97")


@patch("ngRadar_Website.management.commands.dsoc_sim.gbtEvent") # fake a gbtEvent record, let's you bypass having to connect to postres to test logic
def test_db_import_empty_result(mock_gbt_event):
    """Scenario 2: Returns None when no matching UUID exists in the table."""
    mock_gbt_event.objects.filter.return_value.values_list.return_value.first.return_value = None

    result = DB_import("non-existent-uuid")
    
    assert result is None

# ==============================================================================
# 2. DB_columns Test
# ==============================================================================

@patch("ngRadar_Website.management.commands.dsoc_sim.datetime")
def test_db_columns_mapping(mock_datetime):
    """Scenario 1: Verify correct structural mapping of tuple elements into fields."""
    fixed_now = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = fixed_now
    
    gbt_data = ("obj_999", "Jupiter", "SquareWave", fixed_now)
    
    result = DB_columns(gbt_data)
    
    assert result["object_id"] == "obj_999"
    assert result["target"] == "Jupiter"
    assert result["event_time"] == fixed_now

# ==============================================================================
# 3. publish_DB COMPONENT TESTS
# ==============================================================================

@patch("ngRadar_Website.management.commands.dsoc_sim.dsocEvent") # fake a dsocEvent record, let's you bypass having to connect to postres to test logic
def test_publish_db_success(mock_dsoc_event):
    """Scenario 1: Valid payload correctly creates and outputs the model instance."""
    input_data = {"object_id": "obj_1", "target": "Venus"}
    mock_instance = MagicMock()
    mock_dsoc_event.objects.create.return_value = mock_instance

    record = publish_DB("keys/img.png", 2048, input_data)

    assert record == mock_instance
    mock_dsoc_event.objects.create.assert_called_once_with(
        object_id="obj_1", target="Venus", image_key="keys/img.png", num_bytes=2048
    )


@patch("ngRadar_Website.management.commands.dsoc_sim.dsocEvent")
def test_publish_db_exception(mock_dsoc_event):
    """Scenario 2: Handled database crash returns None instead of crashing runtime."""
    mock_dsoc_event.objects.create.side_effect = Exception("DB Connection Timeout")

    record = publish_DB("keys/img.png", 100, {})

    assert record is None

# ==============================================================================
# 4. create_img Test
# ==============================================================================

def test_create_img_output():
    """Ensure the function returns a BytesIO object with non-zero content."""
    tx_waveform = "SineWave"
    img_file, num_bytes = create_img(tx_waveform)
    
    assert isinstance(img_file, bytes)
    assert num_bytes > 0
    assert num_bytes == len(img_file)



# ==============================================================================
# 5. save_image_to_seaweedfs Test
# ==============================================================================

@patch("ngRadar_Website.management.commands.dsoc_sim.boto3") #fake the boto3 module which interacts with seaweedfs
def test_save_image_to_seaweedfs_success(mock_boto3):
    """Scenario 1: Successful upload returns the expected image key."""
    #function inputs:
    target = "Venus"
    image_file = b"fake png bytes"
    uuid = "12345"

    #creating the fake boto3.client:
    mock_instance = MagicMock()
    mock_boto3.client.return_value = mock_instance

    image_key = save_image_to_seaweedfs(target, image_file, uuid)

    assert image_key == f"ddm/{target}/{uuid}.png"
    mock_boto3.client.assert_called_once() #checking that the object store was accessed
    mock_instance.put_object.assert_called_once() #checking that the object store had new data input into it

# ==============================================================================
# 6. consume Test
# ==============================================================================










