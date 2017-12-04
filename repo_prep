script_name = "repo_prep.py"
revision_number = 5
homepage = 'http://forum.xbmc.org/showthread.php?tid=129401'
script_credits = 'All code copyleft (GNU GPL v3) by Unobtanium @ XBMC Forums'

"""
Please bump the version number one decimal point and add your name to credits when making changes.

This is an:
- addons.xml generator
- addons.xml.md5 generator
- optional auto-compressor (including handling of icons, fanart and changelog)

Compression of addons in repositories has many benefits, including:
 - Protects addon downloads from corruption.
 - Smaller addon filesize resulting in faster downloads and less space / bandwidth used on the repository.
 - Ability to "roll back" addon updates in XBMC to previous versions.

To enable the auto-compressor, set the compress_addons setting to True
NOTE: the settings.py of repository aggregator will override this setting.
If you do this you must make sure the "datadir zip" parameter in the addon.xml of your repository file is set to "true".
"""
import os
import shutil
import md5
import zipfile
import re

########## SETTINGS
# Set whether you want your addons compressed or not. Values are True or False
# NOTE: the settings.py of repository aggregator will override this
compress_addons = True

#Optional set a custom directory of where your addons are. False will use the current directory.
# NOTE: the settings.py of repository aggregator will override this
repo_root = False
########## End SETTINGS

# check if repo-prep.py is being run standalone or called from another python file
if __name__ == "__main__":  standalone = True
else: standalone = False

# this 'if' block adds support for the repo aggregator script
# set the repository's root folder here, if the script user has not set a custom path.      
if standalone:
            if repo_root == False: repo_root = os.getcwd()
            print script_name + '  v' + str(revision_number)
            print script_credits
            print 'Homepage and updates: ' + homepage
            print ' '
            
else:
            #so that we can import stuff from parent dir (settings)
            import sys
            sys.path.append('..')
            
            import settings
            repo_root = settings.aggregate_repo_path
            # use repository aggregator settings.py to determine whether to compress
            compress_addons = settings.compress_addons


def is_addon_dir( addon ):
    # this function is used by both classes.
    # very very simple and weak check that it is an addon dir.
    # intended to be fast, not totally accurate.
    # skip any file or .svn folder
    if not os.path.isdir( addon ) or addon == ".svn": return False
    else: return True

                    
class Generator:
    """
        Generates a new addons.xml file from each addons addon.xml file
        and a new addons.xml.md5 hash file. Must be run from the root of
        the checked-out repo. Only handles single depth folder structure.
    """
    def __init__( self ):
    
        #paths
        self.addons_xml = os.path.join( repo_root, "addons.xml" )
        self.addons_xml_md5 = os.path.join( repo_root, "addons.xml.md5" )

        # call master function
        self._generate_addons_files()

    def _generate_addons_files( self ):
        # addon list
        addons = os.listdir( repo_root )

        # final addons text
        addons_xml = u"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n<addons>\n"

        found_an_addon = False
      
        # loop thru and add each addons addon.xml file
        for addon in addons:
            try:
                # skip any file or .svn folder
                if is_addon_dir( addon ):

                        # create path
                        _path = os.path.join( addon, "addon.xml" )

                        if os.path.exists(_path): found_an_addon = True

                        # split lines for stripping
                        xml_lines = open( _path, "r" ).read().splitlines()

                        # new addon
                        addon_xml = ""

                        # loop thru cleaning each line
                        for line in xml_lines:
                            # skip encoding format line
                            if ( line.find( "<?xml" ) >= 0 ): continue
                            # add line
                            addon_xml += unicode( line.rstrip() + "\n", "UTF-8" )

                        # we succeeded so add to our final addons.xml text
                        addons_xml += addon_xml.rstrip() + "\n\n"

            except Exception, e:
                # missing or poorly formatted addon.xml
                print "Excluding %s for %s" % ( _path, e, )

        # clean and add closing tag
        addons_xml = addons_xml.strip() + u"\n</addons>\n"

        # only generate files if we found an addon.xml
        if found_an_addon:
                    # save files
                    self._save_file( addons_xml.encode( "UTF-8" ), self.addons_xml )
                    self._generate_md5_file()
       
                    # notify user
                    print "Updated addons xml and addons.xml.md5 files"
        else: print "Could not find any addons, so script has done nothing."

        


    def _generate_md5_file( self ):
        try:
            # create a new md5 hash
            m = md5.new( open( self.addons_xml ).read() ).hexdigest()

            # save file
            self._save_file( m, self.addons_xml_md5 )

        except Exception, e:
            # oops
            print "An error occurred creating addons.xml.md5 file!\n%s" % ( e, )

    def _save_file( self, data, the_path ):
        try:
            
            # write data to the file
            open( the_path, "w" ).write( data )

        except Exception, e:
            # oops
            print "An error occurred saving %s file!\n%s" % ( the_path, e, )



class Compressor:

   def __init__( self ):
       # variables used later on
       self.addon_name = None
       self.addon_path = None
       self.addon_folder_contents = None
       self.addon_xml = None
       self.addon_version_number = None
       self.addon_zip_path = None

       # run the master method of the class, when class is initialised.
       # only do so if we want addons compressed.
       if compress_addons: self.master()

   def master( self ):
       mydir = os.listdir( repo_root )
       for addon in mydir:

               # set variables
               self.addon_name = str(addon)
               self.addon_path = os.path.join( repo_root, addon )
               
               # skip any file or .svn folder.
               if is_addon_dir( self.addon_path ):
                                  
                       # set another variable
                       self.addon_folder_contents = os.listdir( self.addon_path )

                       # check if addon has a current zipped release in it.
                       addon_zip_exists = self._get_zipped_addon_path()

                       # checking for addon.xml and try reading it.
                       addon_xml_exists = self._read_addon_xml()

                       # generator class relies on addon.xml being in release folder. so if need be, fix a zipped addon release folder lacking an addon.xml
                       if addon_zip_exists:
                               if not addon_xml_exists:
                                       # extract the addon_xml from the zip archive into the addon release folder.
                                       self._extract_addon_xml_to_release_folder()

                       else:
                               if addon_xml_exists:
                                       # now addon.xml has been read, scrape version number from it. we need this when naming the zip (and if it exists the changelog)
                                       self._read_version_number()
                                       print 'Create compressed addon release for -- ' + self.addon_name + '  v' + self.addon_version_number
                                       self._create_compressed_addon_release()

   def _get_zipped_addon_path( self ):
       # get name of addon zip file. returns False if not found.
       for the_file in self.addon_folder_contents:
           if '.zip' in the_file:
                   if ( self.addon_name + '-') in the_file:
                           self.addon_zip_path = os.path.join ( self.addon_path, the_file )
                           return True
       # if loop is not broken by returning the addon path, zip was not found so return False
       self.addon_zip_path = None
       return False
    
   def _extract_addon_xml_to_release_folder():
           the_zip = zipfile.ZipFile( self.addon_zip_path, 'r' )
           for filename in the_zip.namelist():
                        if filename.find('addon.xml'):
                                the_zip.extract( filename, self.addon_path )
                                break
                        
   def _recursive_zipper( self, dir, zip_file ):
            #initialize zipping module
            zip = zipfile.ZipFile( zip_file, 'w', compression=zipfile.ZIP_DEFLATED )

            # get length of characters of what we will use as the root path       
            root_len = len( os.path.dirname(os.path.abspath(dir))   )

            #recursive writer
            for root, dirs, files in os.walk(dir):

                    # subtract the source file's root from the archive root - ie. make /Users/me/desktop/zipme.txt into just /zipme.txt 
                    archive_root = os.path.abspath(root)[root_len:]

                    for f in files:
                            fullpath = os.path.join( root, f )
                            archive_name = os.path.join( archive_root, f )
                            zip.write( fullpath, archive_name, zipfile.ZIP_DEFLATED )
            zip.close()
                   
   def _create_compressed_addon_release( self ):
       # create a zip of the addon into repo root directory, tagging it with '-x.x.x' release number scraped from addon.xml
       zipname = self.addon_name + '-' + self.addon_version_number + '.zip'
       zippath = os.path.join( repo_root, zipname )

       # zip full directories
       self._recursive_zipper( self.addon_path , zippath ) 

       # now move the zip into the addon folder, which we will now treat as the 'addon release directory'
       os.rename( zippath, os.path.join( self.addon_path, zipname ) )
      
       # in the addon release directory, delete every file apart from addon.xml, changelog, fanart, icon and the zip we just constructed. also rename changelog.
       for the_file in self.addon_folder_contents:
           
              the_path = os.path.join( self.addon_path, the_file )

              # delete directories
              if not os.path.isfile( the_path ):
                      shutil.rmtree( the_path )

              # list of files we specifically need to retain for the addon release folder (folder containing the zip                     
              elif not ( ('addon.xml' in the_file) or ('hangelog' in the_file) or ('fanart' in the_file) or ('icon' in the_file) or (zipname in the_file)):
                      os.remove( the_path )

               # tag the changelog with '-x.x.x' release number
              elif 'hangelog' in the_file: # hangelog so that it is detected irrespective of whether C is capitalised
                       changelog = 'changelog-' + self.addon_version_number + '.txt'
                       os.rename( the_path, os.path.join( self.addon_path, changelog ) )
    
   def _read_addon_xml( self ):
      # check for addon.xml and try and read it.
      addon_xml_path = os.path.join( self.addon_path, 'addon.xml' )
      if os.path.exists( addon_xml_path ):
                         
                    # load whole text into string
                    f = open( addon_xml_path, "r") 
                    self.addon_xml = f.read()
                    f.close()

                    # return True if we found and read the addon.xml 
                    return True
      # return False if we couldn't  find the addon.xml 
      else: return False

   def _read_version_number( self ):
      # find the header of the addon.
      headers = re.compile( "\<addon id\=(.+?)>", re.DOTALL ).findall( self.addon_xml )

      for header in headers:

          #if this is the header for the addon, proceed
          if self.addon_name in header:
                              # clean line of quotation characters so that it is easier to read.
                              header = re.sub( '"','', header )
                              header = re.sub( "'",'', header )
                              
                              # scrape the version number from the line
                              self.addon_version_number = (( re.compile( "version\=(.+?) " , re.DOTALL ).findall( header ) )[0]).strip()
              


def execute():
    Compressor()
    Generator()
    
# standalone is equivalent of if name == main   
if standalone: execute()

