# GNU MediaGoblin -- federated, autonomous media hosting
# Copyright (C) 2011, 2012 MediaGoblin contributors.  See AUTHORS.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from mediagoblin.db.base import Session

def check_blog_slug_used(author_id, slug, ignore_b_id=None):
    from mediagoblin.media_types.blog.models import Blog
    query = Blog.query.filter_by(author=author_id, slug=slug)
    if ignore_b_id:
        query = query.filter(Blog.id != ignore_b_id)
    does_exist = query.first() is not None
    return does_exist
    
def may_edit_blogpost(request, blog):
    if request.user.is_admin or request.user.id == blog.author:
        return True
    return False

def set_blogpost_state(request, blogpost):
    if request.form['status'] == 'Publish':
        blogpost.state = u'processed'
    else:
        blogpost.state = u'failed'

def get_all_blogposts_of_blog(request, blog, state=None):
    """Return all blog posts (and metadata) of a blog as query object"""
    # TODO: I would simply make this function a method of the Blog() class.

    # next line is just providing shortcuts
    MediaEntry, BlogPostData = request.db.MediaEntry, request.db.BlogPostData
    blog_posts = Session.query(MediaEntry).join(BlogPostData)\
	.filter(BlogPostData.blog == blog.id)
    if state is not None:
 	blog_posts = blog_posts.filter(MediaEntry.state==state)
    # we could return the metadata (blog_posts_meta) here too and save some queries later
    return blog_posts


