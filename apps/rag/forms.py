import hashlib

from django import forms

from .models import Document


class SourceURLField(forms.URLField):
    """Choose HTTPS for schemeless curator input without a transitional setting."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("assume_scheme", "https")
        super().__init__(*args, **kwargs)


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "authors", "year", "category", "source_url", "licence_note", "file"]
        field_classes = {"source_url": SourceURLField}

    def clean(self):
        cleaned = super().clean()
        uploaded = cleaned.get("file")
        if not self.instance.pk and not uploaded:
            raise forms.ValidationError("Upload the actual PDF before starting ingestion")
        if uploaded and not self.instance.pk:
            digest = hashlib.sha256()
            for block in uploaded.chunks():
                digest.update(block)
            uploaded.seek(0)
            if uploaded.read(5) != b"%PDF-":
                raise forms.ValidationError("The uploaded body is not a PDF")
            uploaded.seek(0)
            sha = digest.hexdigest()
            if Document.objects.filter(sha256=sha).exists():
                raise forms.ValidationError(
                    "This unchanged PDF is already registered; edit its existing tags"
                )
            self.instance.sha256 = sha
            self.instance.size_bytes = uploaded.size
        return cleaned
