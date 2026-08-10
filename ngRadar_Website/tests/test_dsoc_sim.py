from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from ngRadar_Website.enums import Stations, Status
import uuid
from pathlib import Path


# =============================================
# TEST THE STANDALONE FUNCTIONS FROM DSOC_SIM
# =============================================

# ==============================================================================
# IMPORTANT:
# Because we read "ngrok_endpoint.env" on import, we need to patch the Path globally
# before importing all the functions we want to test.
# ==============================================================================
mock_env_data = "BOOTSTRAP_SERVER=localhost:9092\nSOME_OTHER_VAR=value" 
with patch("pathlib.Path.read_text", return_value=mock_env_data):
    from ngRadar_Website.management.commands.dsoc_sim import (
        DB_import,
        DB_columns,
        publish_DB,
        create_img,
        save_image_to_seaweedfs,
        process_msg,
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
    mock_instance = MagicMock()
    mock_dsoc_event.objects.create.return_value = mock_instance

    image_key = "fake_key/img.png"
    num_bytes = 2048
    data = {}
    xmit_station = "XMIT_STATION"
    rcvr_station = "RCVR_STATION"
    transfer_uuid = "TRANSFER_UUID"

    record = publish_DB(image_key=image_key, num_bytes=num_bytes, data=data, xmit_station=xmit_station, rcvr_station=rcvr_station, transfer_uuid=transfer_uuid)

    assert record == mock_instance
    mock_dsoc_event.objects.create.assert_called_once_with(image_key='fake_key/img.png', num_bytes=2048, xmit_station='XMIT_STATION', rcvr_station='RCVR_STATION', transfer_uuid='TRANSFER_UUID', status=Status.COMPLETED)


@patch("ngRadar_Website.management.commands.dsoc_sim.dsocEvent")
def test_publish_db_exception(mock_dsoc_event):
    """Scenario 2: Handled database crash returns None instead of crashing runtime."""
    mock_dsoc_event.objects.create.side_effect = Exception("DB Connection Timeout")

    image_key = "fake_key/img.png"
    num_bytes = 2048
    data = {}
    xmit_station = "XMIT_STATION"
    rcvr_station = "RCVR_STATION"
    transfer_uuid = "TRANSFER_UUID"

    record = publish_DB(image_key=image_key, num_bytes=num_bytes, data=data, xmit_station=xmit_station, rcvr_station=rcvr_station, transfer_uuid=transfer_uuid)

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
    assert img_file.startswith(b"\x89PNG\r\n\x1a\n") #ensures it is in PNG format


# ==============================================================================
# 5. save_image_to_seaweedfs Test
# ==============================================================================

@patch.dict(
    "os.environ",
    {
        "WEED_S3_INTERNAL_DOMAIN": "seaweedfs.fake.com",
        "WEED_S3_ACCESS_KEY": "fake_access_key",
        "WEED_S3_SECRET_KEY": "fake_key",
        "WEED_S3_BUCKET": "fake_bucket",
    },
)
@patch("ngRadar_Website.management.commands.dsoc_sim.create_s3_client") #fake the boto3 module which interacts with seaweedfs
@patch("ngRadar_Website.management.commands.dsoc_sim.upload_seaweedfs")
def test_save_image_to_seaweedfs_success(mock_upload, mock_s3):
    #function inputs:
    target = "Venus"
    image_file = b"fake png bytes"
    dsoc_uuid = "12345"

    #creating the fake boto3.client:
    mock_instance = MagicMock()
    mock_s3.return_value = mock_instance

    image_key = "fake_key/img.png"
    mock_upload.return_value = image_key

    output = save_image_to_seaweedfs(target, image_file, dsoc_uuid)

    assert output == image_key
    mock_s3.assert_called_once()
    mock_upload.assert_called_once_with(mock_instance, f"ddm/Venus/12345.png", b"fake png bytes")

# ==============================================================================
# 6. process_msg Test
# ==============================================================================

#We don't want to actually call all of these functions
#Make a mock of each function to define the fake output we can use:
@patch("ngRadar_Website.management.commands.dsoc_sim.json.loads")
@patch("ngRadar_Website.management.commands.dsoc_sim.uuid.uuid4")
@patch("ngRadar_Website.management.commands.dsoc_sim.record_transfer_event")
@patch("ngRadar_Website.management.commands.dsoc_sim.ETransferEvent")
@patch("ngRadar_Website.management.commands.dsoc_sim.verify_incoming_transfer")
@patch("ngRadar_Website.management.commands.dsoc_sim.DB_import")
@patch("ngRadar_Website.management.commands.dsoc_sim.latency_calc")
@patch("ngRadar_Website.management.commands.dsoc_sim.DB_columns")
@patch("ngRadar_Website.management.commands.dsoc_sim.create_img")
@patch("ngRadar_Website.management.commands.dsoc_sim.save_image_to_seaweedfs")
@patch("ngRadar_Website.management.commands.dsoc_sim.publish_DB") #the arguments for each patch are then listed in reverse order:
def test_process_msg(mock_publish_DB,
                    mock_save_image,
                    mock_create_img,
                    mock_DB_columns,
                    mock_latency_calc,
                    mock_DB_import,
                    mock_verify,
                    mock_etr_event,
                    mock_rec_transfer,
                    mock_uuid,
                    mock_json
                ):
    """Scenario 1: status = transferred"""
    #The fake kafka message in the correct format:
    msg = MagicMock()
    msg.value.return_value = b'{"message"}'

    #giving fake uuid's in the correct format so that 'uuid.UUID()' works on it in the function:
    transfer_uuid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    gbt_uuid = uuid.UUID("22222222-2222-2222-2222-222222222222")

    #The fake output of the json.loads() function:
    mock_payload = {
            "transfer_uuid": str(transfer_uuid),
            "gbt_uuid": str(gbt_uuid),
            "status": int(6),
            "status_label": str("TRANSFERRED"),
            "num_bytes": 2048,
            "filename": str("fake_filename.png"),
            "event_time": datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc),
            "message": str("fake_message"),
            "stations": str("fake_station"),
        }

    mock_json.return_value = mock_payload

    mock_rec_transfer.return_value = None

    filter_values = MagicMock()
    filter_values.exists.return_value = False
    mock_etr_event.objects.filter.return_value = filter_values

    actual_num_bytes = 2048
    mock_verify.return_value = actual_num_bytes

    #pretend that, given the fake uuid, this data is extracted from the DB:
    gbt_data = (
        "obj001",
        "Venus",
        "SineWave",
        datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    )
    
    #Each of these mock return values is pretending that we ran the function, and defining what the fake output is
    mock_DB_import.return_value = gbt_data

    mock_latency_calc.return_value = 1000
    
    data = {
        "event_time": datetime(2026, 7, 16, 12, 0, 0, tzinfo=timezone.utc),
        "object_id": gbt_data[0],
        "target": gbt_data[1],
    }
    mock_DB_columns.return_value = data

    img_file = b"bytes"
    num_bytes = 500
    mock_create_img.return_value = img_file, num_bytes

    mock_uuid.return_value = "54321"

    image_key = f"ddm/'Venus'/54321.png"
    mock_save_image.return_value = image_key

    record = MagicMock()
    mock_publish_DB.return_value = record

    #Now we can call the real function, which will use the defined mock values:
    process_msg(msg)

    #Defining each time mock_rec_transfer was called:
    first = mock_rec_transfer.call_args_list[0]
    second = mock_rec_transfer.call_args_list[1]
    third = mock_rec_transfer.call_args_list[2]

    incoming_file = Path("/dsoc/incoming") / mock_payload.get("filename")

    #This checks whether each function was called with the expected input (meaning that the code works):
    assert mock_rec_transfer.call_count == 3
    assert first.kwargs["status"] == Status.TRANSFERRED
    assert second.kwargs["status"] == Status.VERIFYING
    assert third.kwargs["status"] == Status.COMPLETED
    mock_verify.assert_called_once_with(incoming_file=incoming_file, expected_num_bytes=mock_payload.get("num_bytes"))
    mock_DB_import.assert_called_once_with(gbt_uuid)
    mock_latency_calc.assert_called_once_with(gbt_data[3])
    mock_DB_columns.assert_called_once_with(gbt_data)
    mock_create_img.assert_called_once_with(gbt_data[2])
    mock_save_image.assert_called_once_with(gbt_data[1], img_file, "54321")
    mock_publish_DB.assert_called_once_with(image_key=image_key, num_bytes=num_bytes, data=data, xmit_station=Stations.GBT, rcvr_station=Stations.HN, transfer_uuid=transfer_uuid)