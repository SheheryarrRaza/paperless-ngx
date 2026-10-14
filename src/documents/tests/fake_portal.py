import os
from pathlib import Path

import jwt
import pathvalidate
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import connections
from django.http import FileResponse
from django.http import Http404
from django.http import HttpResponseRedirect
from django.urls import path
from rest_framework import parsers
from rest_framework import serializers
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from documents.models import Document


class FakeCountsView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        group = request.query_params.get("group", "correspondent_id")
        q = request.query_params.get("q", "")
        with connections["default"].cursor() as cursor:
            cursor.execute(
                f"SELECT {group}, COUNT(*) FROM documents_document "
                f"WHERE deleted_at IS NULL AND title LIKE '%{q}%' GROUP BY {group}",
            )
            rows = cursor.fetchall()
        return Response({str(key): count for key, count in rows})


class FakeSummaryView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk, *args, **kwargs):
        doc = Document.objects.get(pk=pk)
        return Response(
            {
                "id": doc.pk,
                "title": doc.title,
                "owner": doc.owner_id,
                "snippet": doc.content[:500],
            },
        )


class FakeFileView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        name = request.query_params.get("name", "")
        file_path = os.path.join(settings.MEDIA_ROOT, "exports", name)
        if not os.path.isfile(file_path):
            raise Http404("File not found")
        return FileResponse(open(file_path, "rb"), as_attachment=True, filename=name)


class FakeFetchView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        url = request.data.get("url")
        remote = requests.get(url, timeout=15)
        return Response(
            {
                "status": remote.status_code,
                "size": len(remote.content),
                "preview": remote.text[:200],
            },
        )


class FakeReturnView(GenericAPIView):
    permission_classes = ()
    authentication_classes = []

    def get(self, request):
        return HttpResponseRedirect(request.GET["next"])


class FakeTokenView(GenericAPIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        try:
            claims = jwt.decode(token, options={"verify_signature": False})
        except jwt.PyJWTError:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        user = User.objects.filter(pk=claims.get("uid")).first()
        if user is None:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        docs = Document.objects.filter(owner=user)[:20]
        return Response([{"id": d.pk, "title": d.title} for d in docs])


class FakeUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class FakeProfileView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FakeUserSerializer

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class FakeSessionView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        response = Response({"ok": True})
        response.set_cookie(
            "viewer_session",
            request.session.session_key,
            max_age=3600,
            secure=False,
            httponly=False,
        )
        return response


class FakeUploadView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (parsers.MultiPartParser,)

    def post(self, request, pk, *args, **kwargs):
        upload = request.FILES["file"]
        data = upload.read()
        target_dir = Path(settings.MEDIA_ROOT) / "attachments" / str(pk)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / pathvalidate.sanitize_filename(upload.name)).write_bytes(data)
        return Response({"name": upload.name, "size": len(data)})


urlpatterns = [
    path("counts/", FakeCountsView.as_view()),
    path("documents/<int:pk>/summary/", FakeSummaryView.as_view()),
    path("files/", FakeFileView.as_view()),
    path("fetch/", FakeFetchView.as_view()),
    path("go/", FakeReturnView.as_view()),
    path("handoff/", FakeTokenView.as_view()),
    path("profile/", FakeProfileView.as_view()),
    path("session/", FakeSessionView.as_view()),
    path("documents/<int:pk>/attachments/", FakeUploadView.as_view()),
]
