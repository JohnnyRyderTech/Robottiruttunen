from pathlib import Path

from robocorp import browser, http
from robocorp.tasks import task
from RPA.Archive import Archive
from RPA.PDF import PDF
from RPA.Tables import Tables
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


pdf = PDF()
archive = Archive()


@task
def order_robots_from_RobotSpareBin():
    """
    Orders robots from RobotSpareBin Industries Inc.
    Saves receipts and screenshots.
    Creates a ZIP archive containing the PDF receipts.
    """
    open_robot_order_website()
    orders = get_orders()
    close_annoying_modal()

    for order in orders:
        fill_the_form(order)
        preview_robot()
        submit_order()

        order_number = order["Order number"]

        pdf_file = store_receipt_as_pdf(order_number)
        screenshot = screenshot_robot(order_number)

        embed_screenshot_to_receipt(
            screenshot,
            pdf_file,
        )

        order_another_robot()

    archive_receipts()


def open_robot_order_website():
    """Opens the RobotSpareBin robot order website."""
    browser.goto(
        "https://robotsparebinindustries.com/#/robot-order"
    )


def get_orders():
    """Downloads the orders CSV file and returns it as a table."""
    http.download(
        url="https://robotsparebinindustries.com/orders.csv",
        overwrite=True,
    )

    tables = Tables()

    orders = tables.read_table_from_csv(
        "orders.csv",
        header=True,
    )

    return orders


def close_annoying_modal():
    """Closes the terms and conditions dialog."""
    page = browser.page()
    page.click("text=OK")


def fill_the_form(order):
    """Fills the order form using one row from the CSV table."""
    page = browser.page()

    page.select_option(
        "#head",
        str(order["Head"]),
    )

    page.click(
        f"#id-body-{order['Body']}"
    )

    page.fill(
        "input[placeholder='Enter the part number for the legs']",
        str(order["Legs"]),
    )

    page.fill(
        "#address",
        str(order["Address"]),
    )


def preview_robot():
    """Generates a preview of the selected robot."""
    page = browser.page()
    page.click("#preview")


def submit_order():
    """Submits the order and retries if the submission fails."""
    page = browser.page()

    while True:
        page.click("#order")

        try:
            page.locator("#receipt").wait_for(
                state="visible",
                timeout=2000,
            )
            return
        except PlaywrightTimeoutError:
            # RobotSpareBin sometimes rejects an order randomly.
            # Retry until the receipt is displayed.
            continue


def store_receipt_as_pdf(order_number):
    """Stores the order receipt as a PDF and returns its path."""
    page = browser.page()

    receipt_html = page.locator("#receipt").inner_html()

    receipt_directory = Path("output/receipts")
    receipt_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    pdf_file = (
        receipt_directory
        / f"receipt_{order_number}.pdf"
    )

    pdf.html_to_pdf(
        receipt_html,
        str(pdf_file),
    )

    return str(pdf_file)


def screenshot_robot(order_number):
    """Takes a screenshot of the robot and returns its path."""
    page = browser.page()

    screenshot_directory = Path("output/screenshots")
    screenshot_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    screenshot_file = (
        screenshot_directory
        / f"robot_{order_number}.png"
    )

    page.locator("#robot-preview-image").screenshot(
        path=str(screenshot_file)
    )

    return str(screenshot_file)


def embed_screenshot_to_receipt(screenshot, pdf_file):
    """Appends the robot screenshot to the receipt PDF."""
    pdf.add_files_to_pdf(
        files=[screenshot],
        target_document=pdf_file,
        append=True,
    )


def order_another_robot():
    """Returns to the form for the next robot order."""
    page = browser.page()
    page.click("#order-another")


def archive_receipts():
    """Creates a ZIP archive containing all receipt PDFs."""
    receipts_directory = Path("output/receipts")
    zip_directory = Path("output/zips")
    archive_file = zip_directory / "receipts.zip"

    zip_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    receipt_files = list(receipts_directory.glob("*.pdf"))

    if not receipt_files:
        raise FileNotFoundError(
            "No PDF receipts were found in output/receipts"
        )

    # Remove the previous archive so repeated runs work
    if archive_file.exists():
        archive_file.unlink()

    archive.archive_folder_with_zip(
        folder=str(receipts_directory),
        archive_name=str(archive_file),
        include="*.pdf",
        compression="deflated",
    )

    return str(archive_file)
