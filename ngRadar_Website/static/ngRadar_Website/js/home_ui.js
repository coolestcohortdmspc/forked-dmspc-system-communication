// =========================================================
// Generic DOM helpers
// =========================================================

function setText(
    id,
    value,
    fallback = "-"
) {
    const element =
        document.getElementById(id);

    if (!element) {
        return;
    }

    element.textContent = value ?? fallback;}


function setHidden(
    id,
    hidden
) {
    const element = document.getElementById(id);

    if (!element) {
        return;
    }

    element.classList.toggle(
        "d-none",
        hidden
    );
}


// =========================================================
// Global system status
// =========================================================

function updateSystemStatus(data) {
    const label =
        data.status_label
        ?? data.status_name
        ?? data.status
        ?? "Active";

    const message =
        data.message
        ?? "";

    setText(
        "system-status-label",
        label,
        ""
    );

    setText(
        "system-status-message",
        message,
        ""
    );
}


// =========================================================
// GBT panel
// =========================================================

function updateGbtPanel(event) {
    const data = event.detail;

    setText(
        "gbt-status",
        data.status_label
            ?? data.status_name
            ?? data.status
    );

    setText(
        "gbt-target",
        data.target
    );

    setText(
        "gbt-object-id",
        data.object_id
    );

    setText(
        "gbt-waveform",
        data.tx_waveform
    );

    setText(
        "gbt-recorded-waveform",
        data.rec_waveform
    );

    setText(
        "gbt-message",
        data.message
    );

    updateSystemStatus(
        data
    );
}


// =========================================================
// VLBA state
// =========================================================

function updateVlbaState(event) {
    const data = event.detail;
    updateSystemStatus(
        data
    );
}

// =========================================================
// VLBA eTransfer Progress Rows
// =========================================================

function createProgressRow(
    stationId,
    stationName
) {
    const list =
        document.getElementById(
            "vlba-progress-list"
        );

    if (!list) {
        return null;
    }

    const row =
        document.createElement(
            "div"
        );

    row.id =
        `progress-${stationId}`;

    row.className =
        "mb-3";

    row.innerHTML = `
        <div
            class="d-flex
                   justify-content-between"
        >
            <strong>
                VLBA-${stationName}
            </strong>

            <span
                class="progress-bytes"
            >
                0 B / 0 B
            </span>
        </div>

        <div
            class="progress"
            role="progressbar"
            aria-valuemin="0"
            aria-valuemax="100"
        >
            <div
                class="progress-bar"
                style="width: 0%"
                aria-valuenow="0"
            >
                0%
            </div>
        </div>
    `;

    list.appendChild(row);

    return row;
}

function updateProgressState(event) {
    const data = event.detail;

    console.log(
        "[Home] Progress update:",
        data
    );

    const stationId =
        Number(data.station);

    const stationName =
        data.station_name;

    if (
        !stationId
        || !stationName
    ) {
        console.error(
            "[Home] Invalid progress payload:",
            data
        );

        return;
    }

    let row =
        document.getElementById(
            `progress-${stationId}`
        );

    if (!row) {
        row = createProgressRow(
            stationId,
            stationName
        );
    }

    if (!row) {
        return;
    }

    const percent =
        Math.min(
            100,
            Math.max(
                0,
                Number(
                    data.percent || 0
                )
            )
        );

    const bar =
        row.querySelector(
            ".progress-bar"
        );

    if (bar) {
        bar.style.width =
            `${percent}%`;

        bar.setAttribute(
            "aria-valuenow",
            percent
        );

        bar.textContent =
            `${percent.toFixed(1)}%`;
    }

    const bytes =
        row.querySelector(
            ".progress-bytes"
        );

    if (bytes) {
        bytes.textContent =
            `${formatBytes(
                data.received_bytes
            )} / ${formatBytes(
                data.total_bytes
            )}`;
    }
}




function formatBytes(bytes) {
    const value =
        Number(bytes || 0);

    if (value === 0) {
        return "0 B";
    }

    const units = [
        "B",
        "KB",
        "MB",
        "GB",
    ];

    const index = Math.min(
        Math.floor(
            Math.log(value)
            / Math.log(1024)
        ),
        units.length - 1
    );

    return (
        (
            value
            / Math.pow(
                1024,
                index
            )
        ).toFixed(1)
        + " "
        + units[index]
    );
}


// =========================================================
// DSOC panel
// =========================================================

function updateDsocPanel(event) {
    const data = event.detail;

    setText(
        "dsoc-message",
        data.message,
        ""
    );

    updateSystemStatus(
        data
    );
}


function showDsocImage(data) {
    // TODO: @ T !!
    // Home receives the live DSOC COMPLETED event before the
    // DB consumer is guaranteed to have persisted ObservatoryEvent.
    //
    // The image already exists in SeaweedFS, but serve_image()
    // currently looks up image_key through ObservatoryEvent first.
    // This creates a race between the live UI path and DB persistence.
    //
    // Home should eventually retrieve the DDM independently of the
    // ObservatoryEvent persistence path.
    const image =
        document.getElementById(
            "dsoc-image"
        );

    if (!image) {
        return;
    }

    image.src =
        `/home/image/${data.event_uuid}/`;

    image.classList.remove(
        "d-none"
    );

    setHidden(
        "dsoc-image-empty",
        true
    );

    const heading =
        document.getElementById(
            "dsoc-image-heading"
        );

    if (heading) {
        heading.textContent =
            "DDM updated from DSOC";
    }
}


// =========================================================
// Waveform submission button
// =========================================================

function lockSubmitButton() {
    const button =
        document.getElementById(
            "waveform-submit-btn"
        );

    if (!button) {
        return;
    }

    button.disabled = true;
    button.textContent =
        "Generating ...";
}


function unlockSubmitButton() {
    const button =
        document.getElementById(
            "waveform-submit-btn"
        );

    if (!button) {
        return;
    }

    button.disabled = false;
    button.textContent =
        "Submit";
}

async function initializeSubmitLock() {
    const button =
        document.getElementById(
            "waveform-submit-btn"
        );

    if (!button) {
        return;
    }

    try {
        const response = await fetch(
            "/home/lock-status/"
        );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const data =
            await response.json();

        if (data.locked) {
            lockSubmitButton();
        } else {
            unlockSubmitButton();
        }

    } catch (error) {
        console.error(
            "[Home] Could not determine "
            + "initial submit lock:",
            error
        );

        button.disabled = true;
        button.textContent =
            "Lock unavailable";
    }
}


initializeSubmitLock();


// =========================================================
// Browser event listeners
// =========================================================

document.body.addEventListener(
    "gbtChanged",
    updateGbtPanel
);


document.body.addEventListener(
    "vlbaChanged",
    updateVlbaState
);


document.body.addEventListener(
    "dsocChanged",
    updateDsocPanel
);


document.body.addEventListener(
    "statusChanged",
    (event) => {
        updateSystemStatus(
            event.detail
        );
    }
);




// A waveform submission starts a new operation.
// GBT activity confirms that processing has begun.

document.body.addEventListener(
    "gbtChanged",
    () => {
        lockSubmitButton();
    }
);


// Unlock submit_waveform button once DSOC reports completion or failure.
document.body.addEventListener(
    "dsocChanged",
    (event) => {
        const data = event.detail;

        if (
            data.status_name === "COMPLETED" ||
            data.status_name === "FAILED"
        ) {
            unlockSubmitButton();
        }
    }
);

document.body.addEventListener(
    "progressChanged",
    updateProgressState
);


