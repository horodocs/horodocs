import io
from datetime import datetime
from xml.sax.saxutils import escape

from settings import CONTACT_EMAIL, CONTACT_NOM, HORODOCS_HEADER_IMG_URL
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    ListItem,
    ListFlowable,
)
from reportlab.lib.pdfencrypt import StandardEncryption
from dotenv import load_dotenv
from pathlib import Path
import os
from gettext import gettext as _
import gettext


class PdfCreator:
    """Build a PDF file. Contains all the methods used to build it."""

    #: Size of the pdf
    width, height = A4

    def __init__(self, file_name, language, password):
        """Create a new almost blank pdf.

        Uses :ref:`CONTACT_NOM <constants>`

        :param file_name: Name of the pdf
        :type file_name: str
        """
        self.lang = gettext.translation(
            "tree", localedir="locales", languages=[language]
        )
        self.lang.install()
        self.buffer = io.BytesIO()
        self.filename = file_name

        encrypt = None
        if password:
            encrypt = StandardEncryption(password)
        self.document = SimpleDocTemplate(
            self.buffer,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=(15 + 40) * mm,
            bottomMargin=25 * mm,
            title=file_name,
            author=CONTACT_NOM,
            creator="ESC - UNIL",
            subject="Quittance",
            encrypt=encrypt,
        )

        self.styles = getSampleStyleSheet()
        self.styles.add(
            ParagraphStyle(
                name="Infos",
                borderWidth=1,
                borderColor="grey",
                leading=12,
                spaceBefore=6,
                borderPadding=5,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="PNG",
                borderWidth=1,
                borderColor="#dddddd",
                fontSize=8,
                leading=8.8,
                leftIndent=36,
                spaceBefore=3,
                fontName="Courier",
                borderPadding=5,
            )
        )
        self.styles.add(ParagraphStyle(name="NormalSmall", fontSize=9, leading=12))
        self.styles.add(
            ParagraphStyle(
                name="RectInfos",
                fontSize=10,
                leading=12,
                borderWidth=1,
                borderColor=colors.black,
                borderPadding=8,
                backColor=colors.lightgrey,
                leftIndent=10,
                rightIndent=10,
            )
        )

        self.elements = []

    def add_title(self, title):
        """Add the PDF tilte

        :param title: Title of the PDF
        :type title: str
        """
        self.elements.append(Paragraph(title, self.styles["Title"]))

    def add_qr_code(self, qr_code_name, qr_code_content):
        """Add the qr code to the PDF.

        :param qr_code_name: Name of the QR code
        :type qr_code_name: str
        :param qr_code_content: Content of the qr code
        :type qr_code_content: str
        """
        qr_code = Image(qr_code_name, 50 * mm, 50 * mm)
        self.elements.append(qr_code)

        link = "<link href={0}>{0}</link>".format(
            str(qr_code_content.decode()).replace("&", "&amp;")
        )
        self.elements.append(Paragraph(link, self.styles["PNG"]))
        self.elements.append(Paragraph(3 * "\n", self.styles["Normal"]))
        self.elements.append(Spacer(209, 15))

    def add_category(self, category_name):
        """Add a category in the PDF as a title.

        :param category_name: Name of the category
        :type category_name: str
        """
        self.elements.append(Paragraph(category_name, self.styles["Heading1"]))

    def add_information_rect(self, text):
        """Add informations in a rectangle in the PDF.

        :param text: Text with the informations
        :type text: str
        """
        p = Paragraph(text, self.styles["RectInfos"])
        self.elements.append(p)
        self.__add_canevas_spacer()

    def add_technical_informations(
        self, explain_text, salt, anterior_branches, posterior_branches, version
    ):
        """Add all the technical informations in the pdf

        :param explain_text: Explication of the technical informations
        :type explain_text: str
        :param salt: Salt used during the horodating process
        :type salt: str
        :param anterior_branches: Anterior branches used to calculate the merkle based tree
        :type anterior_branches: List[str]
        :param posterior_branches: posterior branches used to calculate the merkle based tree
        :type posterior_branches: List[str]
        :param version: Version of the system
        :type version: int
        """
        _ = self.lang.gettext
        dotenv_path = (
            Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / ".env"
        )
        load_dotenv(dotenv_path)
        documentation_address = os.environ.get("HORODOCS_URL_DOCS")
        github_link = os.environ.get("HORODOCS_GIT_PUBLIC")
        self.elements.append(Paragraph(explain_text, self.styles["Normal"]))
        self.elements.append(
            ListFlowable(
                [
                    ListItem(
                        Paragraph(
                            _(
                                '<b>Version : </b> {} - <a href="{}">Lien documentation</a> - <a href="{}">Lien Github</a>'
                            ).format(version, documentation_address, github_link),
                            self.styles["Normal"],
                        ),
                        leftIndent=24,
                    ),
                    ListItem(
                        Paragraph(
                            _("<b>Sel :</b> {}").format(salt), self.styles["Normal"]
                        ),
                        leftIndent=24,
                    ),
                ],
                bulletType="bullet",
                start="bulletchar",
                leftIndent=12,
                spaceBefore=12,
                spaceAfter=12,
            )
        )
        self.add_anterior_branches(anterior_branches)
        self.add_posterior_branches(posterior_branches)

    def add_horodatage_trace(self, time):
        """Add the submitted date to the PDF.

        :param time: Date of the submission
        :type time: str
        """
        _ = self.lang.gettext
        horodatage = _("<b>Horodatage :</b>")
        self.elements.append(Paragraph(horodatage, self.styles["Normal"]))
        self.elements.append(
            ListFlowable(
                [
                    ListItem(
                        Paragraph(
                            _(
                                '<font color="blue"><b>Date et heure de la requête d\'horodatage :</b> {}</font>'
                            ).format(time),
                            self.styles["Normal"],
                        ),
                        bulletColor="blue",
                        leftIndent=24,
                    )
                ],
                bulletType="bullet",
                start="bulletchar",
                leftIndent=12,
                spaceBefore=12,
                spaceAfter=12,
            )
        )

    def add_blockchain_values(self, lid, time, blockchain):
        """Add all the blockchain values in a list in the pdf.

        :param lid: "Witness" value
        :type lid: str
        :param time: Time of the end of the merkle based tree
        :type time: str
        :param blockchain: Name of the blockchain used
        :type blockchain: str
        """
        _ = self.lang.gettext
        self.elements.append(
            ListFlowable(
                [
                    ListItem(
                        Paragraph(
                            _("<b>Blockchain :</b> {}").format(blockchain),
                            self.styles["Normal"],
                        ),
                        leftIndent=24,
                    ),
                    ListItem(
                        Paragraph(
                            _(
                                '<font color="blue"><b>Valeur de contrôle :</b> {}</font>'
                            ).format(lid),
                            self.styles["Normal"],
                        ),
                        bulletColor="blue",
                        leftIndent=24,
                        spaceBefore=4,
                    ),
                    ListItem(
                        Paragraph(
                            _(
                                '<font color="blue"><b>Date et heure de la soumission dans la blockchain :</b> {}</font>'
                            ).format(time),
                            self.styles["Normal"],
                        ),
                        bulletColor="blue",
                        leftIndent=24,
                        spaceBefore=4,
                    ),
                ],
                bulletType="bullet",
                start="bulletchar",
                leftIndent=12,
                spaceBefore=4,
            )
        )
        self.__add_canevas_spacer()

    def add_anterior_branches(self, anterior_branches):
        """Add all anterior branches line by line to the PDF.

        :param anterior_branches: All the anterior branches.
        :type anterior_branches: List[str]
        """
        _ = self.lang.gettext
        txt_leaves = ""
        anterior_branches_text = _("<b>Embranchement(s) antérieur(s) : </b>")
        self.elements.append(Paragraph(anterior_branches_text, self.styles["Normal"]))

        if len(anterior_branches) == 0:
            self.elements.append(
                ListFlowable(
                    [
                        ListItem(
                            Paragraph(
                                _("Il n'y a pas d'embranchement antérieur dans ce cas"),
                                self.styles["Normal"],
                            ),
                            leftIndent=24,
                        )
                    ],
                    bulletType="bullet",
                    start="bulletchar",
                    leftIndent=12,
                    spaceBefore=12,
                    spaceAfter=12,
                )
            )
        else:
            items = []
            for l in anterior_branches:
                txt_leaves = f"({l[0]},{l[1]}) - {l[2]}\n"
                items.append(
                    ListItem(
                        Paragraph(txt_leaves, self.styles["Normal"]), leftIndent=24
                    )
                )
            self.elements.append(
                ListFlowable(
                    items,
                    bulletType="bullet",
                    start="bulletchar",
                    leftIndent=12,
                    spaceBefore=12,
                    spaceAfter=12,
                )
            )

    def add_posterior_branches(self, posterior_branches):
        """Add all posterior branches line by line to the PDF.

        :param posterior_branches: All the posterior branches.
        :type posterior_branches: List[str]
        """
        _ = self.lang.gettext
        txt_leaves = ""
        posterior_branches_text = _("<b>Embranchement(s) postérieur(s) : </b>")
        self.elements.append(Paragraph(posterior_branches_text, self.styles["Normal"]))
        if len(posterior_branches) == 0:
            self.elements.append(
                ListFlowable(
                    [
                        ListItem(
                            Paragraph(
                                _(
                                    "Il n'y a pas d'embranchement postérieur dans ce cas"
                                ),
                                self.styles["Normal"],
                            ),
                            leftIndent=24,
                        )
                    ],
                    bulletType="bullet",
                    start="bulletchar",
                    leftIndent=12,
                    spaceBefore=12,
                    spaceAfter=12,
                )
            )
        else:
            items = []
            for l in posterior_branches:
                txt_leaves = f"({l[0]},{l[1]}) - {l[2]}\n"
                items.append(
                    ListItem(
                        Paragraph(txt_leaves, self.styles["Normal"]), leftIndent=24
                    )
                )
            self.elements.append(
                ListFlowable(
                    items,
                    bulletType="bullet",
                    start="bulletchar",
                    leftIndent=12,
                    spaceBefore=12,
                    spaceAfter=12,
                )
            )

    def add_empreintes_trace(self, hash_md5, hash_sha256):
        """Add all the associated file's hashes.

        :param hash_md5: MD5 hash of the file.
        :type hash_md5: str
        :param hash_sha256: SHA256 hash of the file.
        :type hash_sha256: str
        """
        _ = self.lang.gettext
        hash_text = _("<b>Empreintes du fichier :</b>")
        self.elements.append(Paragraph(hash_text, self.styles["Normal"]))
        self.elements.append(
            ListFlowable(
                [
                    ListItem(
                        Paragraph(
                            _('<font color="blue"><b>MD5 :</b> {}</font>').format(
                                hash_md5
                            ),
                            self.styles["Normal"],
                        ),
                        bulletColor="blue",
                        leftIndent=24,
                    ),
                    ListItem(
                        Paragraph(
                            _('<font color="blue"><b>SHA256 :</b> {}</font>').format(
                                hash_sha256
                            ),
                            self.styles["Normal"],
                        ),
                        bulletColor="blue",
                        leftIndent=24,
                        spaceBefore=4,
                    ),
                ],
                bulletType="bullet",
                start="bulletchar",
                leftIndent=12,
                spaceBefore=4,
            )
        )
        self.__add_canevas_spacer()

    def add_informations_trace(
        self, case_number, trace_id, investigator, custom_text=""
    ):
        """Add all the file informations submitted by the user to the PDF.

        :param case_number: Case number linked to the submitted file.
        :type case_number: str
        :param trace_id: ID of the trace.
        :type trace_id: str
        :param investigator: ID of the investigator
        :type investigator: str
        :param custom_text: Custom text added by the investigator.
        :type custom_text: str
        """
        _ = self.lang.gettext

        text_libre = custom_text.replace("\n", "<br/>")
        self.elements.append(
            ListFlowable(
                [
                    ListItem(
                        Paragraph(
                            _("<b>Identifiant du cas :</b> {}").format(
                                escape(case_number)
                            ),
                            self.styles["Normal"],
                        ),
                        leftIndent=24,
                    ),
                    ListItem(
                        Paragraph(
                            _("<b>Identifiant du fichier :</b> {}").format(
                                escape(trace_id)
                            ),
                            self.styles["Normal"],
                        ),
                        leftIndent=24,
                        spaceBefore=4,
                    ),
                    ListItem(
                        Paragraph(
                            _("<b>Identifiant de l'enquêteur :</b> {}").format(
                                escape(investigator)
                            ),
                            self.styles["Normal"],
                        ),
                        leftIndent=24,
                    ),
                    ListItem(
                        Paragraph(_("<b>Texte libre :</b>"), self.styles["Normal"]),
                        leftIndent=24,
                        spaceBefore=4,
                    ),
                ],
                bulletType="bullet",
                start="bulletchar",
                leftIndent=12,
                spaceBefore=4,
            )
        )
        if text_libre != "":
            try:
                self.elements.append(Paragraph(text_libre, self.styles["Infos"]))
            except ValueError:
                try:
                    self.elements.append(
                        Paragraph(
                            "<b>ERREUR DANS LES BALISES HTML UTILISÉES</b><br/>"
                            + escape(text_libre, {"&lt;br/&gt;": "<br/>"}),
                            self.styles["Infos"],
                        )
                    )
                except ValueError:
                    text_libre = text_libre.split("<br/>")
                    for texte in text_libre:
                        self.elements.append(
                            ListItem(
                                Paragraph(texte.replace("<", "%"), self.styles["Infos"])
                            )
                        )
        self.__add_canevas_spacer()

    def build_pdf(self):
        """Build the PDF.

        :return: The PDF.
        :rtype: io.BytesIO
        """
        self.document.build(
            self.elements, onFirstPage=self.footer, onLaterPages=self.footer
        )
        self.buffer.seek(0)
        return self.buffer

    def __add_canevas_spacer(self):
        """Add a space in the PDF."""
        canevas = Spacer(self.width, 5 * mm)
        self.elements.append(canevas)

    def footer(self, canevas, doc):
        """To build the footer and header. Containing all contact informations and references.

        Uses :ref:`CONTACT_EMAIL <constants>`, :ref:`HORODOCS_HEADER_IMG_URL <constants>`

        :param canevas: Canvas of the PDF.
        :type canevas:
        :param doc: Not used be necessary to work with SimpleDocTemplate
        :type doc:
        """
        _ = self.lang.gettext
        now = datetime.now().strftime("%Y-%m-%d; %H:%M:%S")
        canevas.saveState()
        header = HORODOCS_HEADER_IMG_URL
        canevas.drawImage(
            header,
            width=180 * mm,
            height=34 * mm,
            x=15 * mm,
            y=A4[1] - 15 * mm - 34 * mm,
        )

        canevas.setFillColorRGB(0.90, 0.90, 0.90)
        canevas.rect(14 * mm, 8 * mm, self.width - 2 * 10 * mm, 12 * mm, fill=1)
        canevas.setFillColorRGB(0, 0, 0)

        canevas.setFont("Helvetica", 7)
        canevas.drawString(15 * mm, 10 * mm, "Contact: {}".format(CONTACT_EMAIL))
        canevas.drawString(3 * A4[0] / 4, 10 * mm, self.filename)

        canevas.setFont("Helvetica", 9)
        canevas.drawString(15 * mm, 15 * mm, _("ESC - Université de Lausanne"))
        canevas.drawString(A4[0] / 2, 15 * mm, "-{}-".format(canevas.getPageNumber()))
        canevas.drawString(3 * A4[0] / 4, 15 * mm, _("Créé le {}").format(now))
        canevas.restoreState()
