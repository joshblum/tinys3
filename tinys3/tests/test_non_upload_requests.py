# -*- coding: utf-8 -*-
import os
import unittest
from flexmock import flexmock
from tinys3.request_factory import CopyRequest, S3Request, UpdateMetadataRequest, DeleteRequest, GetRequest
from tinys3 import Connection


class TestNonUploadRequests(unittest.TestCase):
    def setUp(self):
        """
        Create a default connection
        """
        self.conn = Connection("TEST_ACCESS_KEY", "TEST_SECRET_KEY", tls=True)

    def test_url_generation(self):
        """
        Check that the url generation function works properly
        """

        r = S3Request(self.conn)

        # Simple with tls
        url = r.bucket_url('test_key', 'test_bucket')
        self.assertEqual(url, 'https://s3.amazonaws.com/test_bucket/test_key', 'Simple url with SSL')

        # change connection to non-http
        self.conn.tls = False

        r = S3Request(self.conn)

        # Test the simplest url
        url = r.bucket_url('test_key', 'test_bucket')
        self.assertEqual(url, 'http://s3.amazonaws.com/test_bucket/test_key', 'Simple url')

        # Key with / prefix
        url = r.bucket_url('/test_key', 'test_bucket')
        self.assertEqual(url, 'http://s3.amazonaws.com/test_bucket/test_key', 'Key with / prefix')

        # Nested key
        url = r.bucket_url('folder/for/key/test_key', 'test_bucket')
        self.assertEqual(url, 'http://s3.amazonaws.com/test_bucket/folder/for/key/test_key', 'Nested key')

    def _mock_adapter(self, request):
        """
        Creates a mock object and replace the result of the adapter method with is
        """
        mock_obj = flexmock()
        flexmock(request).should_receive('adapter').and_return(mock_obj)

        return mock_obj

    def test_delete_request(self):
        """
        Test the generation of a delete request
        """

        r = DeleteRequest(self.conn, 'key_to_delete', 'bucket')

        mock = self._mock_adapter(r)

        mock.should_receive('delete').with_args('https://s3.amazonaws.com/bucket/key_to_delete',
                                                auth=self.conn.auth).and_return(self._mock_response()).once()

        r.run()

    def test_get_request(self):
        """
        Test the generation of a get request
        """
        stream = False
        r = GetRequest(self.conn, 'key_to_get', 'bucket', stream)

        mock = self._mock_adapter(r)

        mock.should_receive('get').with_args('https://s3.amazonaws.com/bucket/key_to_get',
                                             auth=self.conn.auth, stream=stream).and_return(self._mock_response()).once()

        r.run()

    def test_get_with_dst_filename(self):
        """
        Test the generation of a get request
        """
        stream = True
        r = GetRequest(self.conn, 'key_to_get', 'bucket', stream, dst_filename='foo')

        mock = self._mock_adapter(r)
        mock_res = flexmock(
            raise_for_status=lambda: None,
            iter_lines=lambda: iter(['foo', 'bar', 'baz']),
            )

        mock.should_receive('get').with_args('https://s3.amazonaws.com/bucket/key_to_get',
                                             auth=self.conn.auth, stream=stream).and_return(mock_res).once()

        filename = r.run()
        self.assertTrue(os.path.isfile(filename))
        os.remove(filename)


    def test_update_metadata(self):
        """
        Test the generation of an update metadata request
        """

        r = UpdateMetadataRequest(self.conn, 'key_to_update', 'bucket', {'example-meta-key': 'example-meta-value'},
                                  True)

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-copy-source': '/bucket/key_to_update',
            'x-amz-metadata-directive': 'REPLACE',
            'x-amz-acl': 'public-read',
            'example-meta-key': 'example-meta-value'
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/bucket/key_to_update',
            headers=expected_headers,
            auth=self.conn.auth
        ).and_return(self._mock_response()).once()

        r.run()

    def test_copy(self):
        """
        Test the generation of a copy request
        """

        r = CopyRequest(self.conn, 'from_key', 'from_bucket', 'to_key', 'to_bucket', None, False)

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-copy-source': '/from_bucket/from_key',
            'x-amz-metadata-directive': 'COPY',
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/to_bucket/to_key',
            headers=expected_headers,
            auth=self.conn.auth
        ).and_return(self._mock_response()).once()

        r.run()

    def _mock_response(self):
        """
        Create a mock response with 'raise_for_status' method
        """

        return flexmock(raise_for_status=lambda: None)
