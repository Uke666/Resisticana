import discord
from discord.ext import commands
import logging
from utils.database import Database

class Company(commands.Cog):
    """Cog for handling company-related commands and features."""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        
    @commands.command(name="createcompany", aliases=["newcompany"])
    async def create_company(self, ctx, *, company_name: str):
        """Create a new company (requires higher role)."""
        user_id = ctx.author.id
        
        # Check if user has permission to create a company (higher role)
        # Higher roles are: Owner, Admin, Moderator/staff, level 50, level 35
        allowed_role_ids = [
            "1352694494843240448",  # Owner
            "1352694494813749308",  # Admin
            "1352694494813749307",  # Moderator/staff
            "1352694494813749299",  # level 50
            "1352694494797234237"   # level 35
        ]
        
        has_permission = False
        for role in ctx.author.roles:
            if str(role.id) in allowed_role_ids:
                has_permission = True
                break
                
        if not has_permission:
            await ctx.send("You don't have permission to create a company! You need a higher role.")
            return
            
        # Attempt to create the company
        result = self.db.create_company(user_id, company_name)
        
        if result["success"]:
            embed = discord.Embed(
                title="Company Created",
                description=f"Congratulations! You've created '{company_name}'!",
                color=discord.Color.green()
            )
            embed.add_field(name="Owner", value=ctx.author.mention, inline=False)
            embed.add_field(name="Next Steps", value="Invite members using `!invite @user`", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Error: {result['message']}")
            
    @commands.command(name="company")
    async def company_info(self, ctx, *, company_name: str = None):
        """Display information about a company or your company."""
        user_id = ctx.author.id
        
        if company_name:
            # Look up specific company
            company_data = self.db.get_company_by_name(company_name)
        else:
            # Look up user's company
            company_data = self.db.get_user_company(user_id)
            
        if not company_data:
            if company_name:
                await ctx.send(f"Company '{company_name}' not found!")
            else:
                await ctx.send("You are not part of any company! Join one or create your own.")
            return
            
        # Get owner name
        owner = ctx.guild.get_member(company_data["owner_id"])
        owner_name = owner.display_name if owner else f"User {company_data['owner_id']}"
        
        # Get employee names
        employees = []
        for emp_id in company_data["employees"]:
            member = ctx.guild.get_member(emp_id)
            if member:
                employees.append(member.display_name)
            else:
                employees.append(f"User {emp_id}")
                
        embed = discord.Embed(
            title=f"{company_data['name']} - Company Info",
            color=discord.Color.blue()
        )
        embed.add_field(name="Owner", value=owner_name, inline=False)
        embed.add_field(name="Created", value=company_data["created_at"].strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Employees", value=len(employees), inline=True)
        
        if employees:
            embed.add_field(name="Employee List", value=", ".join(employees[:10]) + 
                ("..." if len(employees) > 10 else ""), inline=False)
            
        await ctx.send(embed=embed)
    
    @commands.command(name="invite")
    async def invite_to_company(self, ctx, member: discord.Member):
        """Invite a user to your company."""
        owner_id = ctx.author.id
        invitee_id = member.id
        
        if owner_id == invitee_id:
            await ctx.send("You can't invite yourself!")
            return
            
        # Check if user owns a company
        company_data = self.db.get_user_owned_company(owner_id)
        
        if not company_data:
            await ctx.send("You don't own a company!")
            return
            
        # Check if invitee is already in a company
        user_company = self.db.get_user_company(invitee_id)
        if user_company:
            await ctx.send(f"{member.display_name} is already in a company!")
            return
            
        # Create an invitation embed
        embed = discord.Embed(
            title="Company Invitation",
            description=f"{ctx.author.display_name} is inviting you to join '{company_data['name']}'!",
            color=discord.Color.gold()
        )
        embed.add_field(name="React to Accept", value="✅ - Accept invitation\n❌ - Decline invitation", inline=False)
        
        # Send invitation
        message = await ctx.send(f"{member.mention}", embed=embed)
        
        # Add reactions
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return user.id == invitee_id and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=300.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Accept invitation
                result = self.db.add_employee_to_company(company_data["id"], invitee_id)
                
                if result["success"]:
                    await ctx.send(f"{member.mention} has joined {company_data['name']}!")
                else:
                    await ctx.send(f"Error: {result['message']}")
            else:
                # Decline invitation
                await ctx.send(f"{member.mention} declined the invitation.")
                
        except asyncio.TimeoutError:
            await ctx.send(f"The invitation to {member.mention} has expired.")
            
    @commands.command(name="leave")
    async def leave_company(self, ctx):
        """Leave your current company."""
        user_id = ctx.author.id
        
        # Check if user is in a company
        company_data = self.db.get_user_company(user_id)
        
        if not company_data:
            await ctx.send("You are not part of any company!")
            return
            
        # Check if user is the owner
        if company_data["owner_id"] == user_id:
            await ctx.send("As the owner, you cannot leave your company. Use `!disband` to disband it instead.")
            return
            
        # Remove user from company
        result = self.db.remove_employee_from_company(company_data["id"], user_id)
        
        if result["success"]:
            await ctx.send(f"You have left '{company_data['name']}'!")
        else:
            await ctx.send(f"Error: {result['message']}")
            
    @commands.command(name="disband")
    async def disband_company(self, ctx):
        """Disband your company as the owner."""
        user_id = ctx.author.id
        
        # Check if user owns a company
        company_data = self.db.get_user_owned_company(user_id)
        
        if not company_data:
            await ctx.send("You don't own a company!")
            return
            
        # Confirm action
        embed = discord.Embed(
            title="Confirm Company Disbanding",
            description=f"Are you sure you want to disband '{company_data['name']}'? This cannot be undone!",
            color=discord.Color.red()
        )
        embed.add_field(name="React to Confirm", value="✅ - Yes, disband company\n❌ - No, keep company", inline=False)
        
        # Send confirmation
        message = await ctx.send(embed=embed)
        
        # Add reactions
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return user.id == ctx.author.id and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Disband company
                result = self.db.delete_company(company_data["id"])
                
                if result["success"]:
                    await ctx.send(f"'{company_data['name']}' has been disbanded.")
                else:
                    await ctx.send(f"Error: {result['message']}")
            else:
                # Cancel disbanding
                await ctx.send(f"Company disbanding cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("Disbanding confirmation timed out.")
            
    @commands.command(name="companies")
    async def list_companies(self, ctx):
        """List all companies on the server."""
        companies = self.db.get_all_companies()
        
        if not companies:
            await ctx.send("There are no companies on this server yet!")
            return
            
        embed = discord.Embed(
            title="Companies Directory",
            description=f"There are {len(companies)} companies on this server",
            color=discord.Color.blue()
        )
        
        for company in companies[:10]:  # Show only the first 10 companies
            owner = ctx.guild.get_member(company["owner_id"])
            owner_name = owner.display_name if owner else f"User {company['owner_id']}"
            
            embed.add_field(
                name=company["name"],
                value=f"👑 Owner: {owner_name}\n👥 Employees: {len(company['employees'])}",
                inline=False
            )
            
        if len(companies) > 10:
            embed.set_footer(text=f"Showing 10 of {len(companies)} companies")
            
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Company(bot))
