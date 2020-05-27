#v.0.5.1

import socket
import requests as _requests

class URL( object ):

    def __init__( self, returntype='text', headers='', timeout=10 ):
        self.TIMEOUT = timeout
        self.HEADERS = headers
        self.RETURNTYPE = returntype


    def Get( self, theurl, **kwargs ):
        return self._urlcall( theurl, 'get', kwargs )


    def Post( self, theurl, **kwargs ):
        return self._urlcall( theurl, 'post', kwargs )


    def Put( self, theurl, **kwargs ):
        return self._urlcall( theurl, 'put', kwargs )


    def Delete( self, theurl, **kwargs ):
        return self._urlcall( theurl, 'delete', kwargs )


    def _urlcall( self, theurl, urltype, kwargs ):
        loglines = []
        urldata = ''
        bad_r = False
        auth, params, thedata = self._unpack_args( kwargs )
        try:
            if urltype == "get":
                urldata = _requests.get( theurl, auth=auth, params=params, headers=self.HEADERS, timeout=self.TIMEOUT )
            elif urltype == "post":
                urldata = _requests.post( theurl, auth=auth, params=params, data=thedata, headers=self.HEADERS, timeout=self.TIMEOUT )
            elif urltype == "put":
                urldata = _requests.put( theurl, auth=auth, params=params, data=thedata, headers=self.HEADERS, timeout=self.TIMEOUT )
            elif urltype == "delete":
                urldata = _requests.delete( theurl, auth=auth, params=params, data=thedata, headers=self.HEADERS, timeout=self.TIMEOUT )
            loglines.append( "the url is: " + urldata.url )
            loglines.append( 'the params are: ')
            loglines.append( params )
            loglines.append( 'the data are: ')
            loglines.append( thedata )
            urldata.raise_for_status()
        except _requests.exceptions.ConnectionError as e:
            loglines.append( 'site unreachable at ' + theurl )
            loglines.append( e )
            bad_r = True
        except _requests.exceptions.Timeout as e:
            loglines.append( 'timeout error while downloading from ' + theurl )
            loglines.append( e )
            bad_r = True
        except socket.timeout as e:
            loglines.append( 'timeout error while downloading from ' + theurl )
            loglines.append( e )
            bad_r = True
        except _requests.exceptions.HTTPError as e:
            loglines.append( 'HTTP Error while downloading from ' + theurl )
            loglines.append( e )
            bad_r = True
        except _requests.exceptions.RequestException as e:
            loglines.append( 'unknown error while downloading from ' + theurl )
            loglines.append( e )
            bad_r = True
        if bad_r:
            return False, loglines, ''
        if urldata:
            success = True
            loglines.append( 'returning URL as ' + self.RETURNTYPE )
            if self.RETURNTYPE == 'text':
                data = urldata.text
            elif self.RETURNTYPE == 'binary':
                data = urldata.content
            elif self.RETURNTYPE == 'json':
                data = urldata.json()
            else:
                loglines.append( 'unable to convert returned object to acceptable type' )
                return False, loglines, ''
        else:
            return False, loglines, ''
        loglines.append( '-----URL OBJECT RETURNED-----' )
        loglines.append( data )
        return urldata.status_code, loglines, data


    def _unpack_args( self, kwargs ):
        try:
            auth = kwargs['auth']
        except KeyError:
            auth = ()
        try:
            params = kwargs['params']
        except KeyError:
            params = {}
        try:
            thedata = kwargs['data']
        except KeyError:
            if self.RETURNTYPE == 'json':
                thedata = []
            else:
                data = ''
        return auth, params, thedata