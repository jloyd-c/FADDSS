"""
Profiling App — Custom Pagination (Phase 3)
══════════════════════════════════════════════════════════════════════════════

Extends DRF's PageNumberPagination with richer response metadata:
  - total_pages  — so the frontend can render a page count indicator
  - page         — current page number (avoids client-side parsing of next URL)
  - page_size    — actual page size used (may be capped by max_page_size)

The page_size is configurable per request via `?page_size=50`.
Default: 20 records. Maximum: 200 records.

Usage:
    class MyViewSet(viewsets.ModelViewSet):
        pagination_class = ProfilingPagination

Response structure:
    {
        "count":       1234,
        "total_pages": 62,
        "page":        3,
        "page_size":   20,
        "next":        "https://.../api/v1/profiling/persons/?page=4",
        "previous":    "https://.../api/v1/profiling/persons/?page=2",
        "results":     [...]
    }
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ProfilingPagination(PageNumberPagination):
    page_size              = 20
    page_size_query_param  = 'page_size'
    max_page_size          = 200
    page_query_param       = 'page'

    def get_paginated_response(self, data):
        return Response({
            'count':       self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'page':        self.page.number,
            'page_size':   self.get_page_size(self.request),
            'next':        self.get_next_link(),
            'previous':    self.get_previous_link(),
            'results':     data,
        })

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'required': ['count', 'total_pages', 'page', 'page_size', 'results'],
            'properties': {
                'count':       {'type': 'integer'},
                'total_pages': {'type': 'integer'},
                'page':        {'type': 'integer'},
                'page_size':   {'type': 'integer'},
                'next':        {'type': 'string', 'nullable': True, 'format': 'uri'},
                'previous':    {'type': 'string', 'nullable': True, 'format': 'uri'},
                'results':     schema,
            },
        }
